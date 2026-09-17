"""Independent re-reduction for the CONFOUND check on finding torque-mode-late-on-small-corrections.

Does NOT reuse s1_goal/_red/*.npz (built by s1_reduce.py) -- reduces straight from the shared v282ref
cache (v282cmp.load) so the check does not inherit any bug in the original reduction. Adds an la_yaw
channel (carState yaw rate * v) alongside la_pose (livePose yaw rate * v, what the finding actually
used -- confirmed by matching s1_results.json's lag_pDa/rE_pD numbers to the finding's magnitude table
before writing this script). One route in RAM at a time.

For each route, band, speed-bin: band-pass (zero-phase butter order-2) the MODEL desired lateral accel
and each achieved channel over the WHOLE run (not the vbin subset, to avoid short-segment edge
artifacts), mask to the speed bin, then per (route, band, vbin, channel) find the lag 0..0.8s that
maximises normalised cross-correlation -- computed PER ROUTE (not pooled across the group) so leave-
one-route-out is a simple re-pool of saved per-route numbers, not a re-run.

Saves decimated (4x, 25 Hz) per-sample arrays (x, env, channel@own-route-lag, channel@route lat_delay,
vbin, chunk id) per route, plus the per-route lag table, to _red/<route>.npz.
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

OUT = Path(__file__).resolve().parent / "_red"
OUT.mkdir(exist_ok=True)
FS = V.FS
BANDS = [(0.15, 0.30), (0.30, 0.60)]
VB = [(8.0, 15.0), (15.0, 22.0), (22.0, 99.0)]
DEC = 4
MAXLAG = int(0.8 * FS)
ROUTES = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac",
          "0000006c--68c6e94b17", "0000006d--05e83bb04f"]


def bp(x, f1, f2):
    sos = signal.butter(2, [f1, f2], btype="band", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x, padtype="even")


def vbin(v):
    b = np.full(len(v), -1, int)
    for k, (a, c) in enumerate(VB):
        b[(v >= a) & (v < c)] = k
    return b


def main(route):
    S = V.load(route)
    t, v = S["t"], S["v"]
    m = V.usable(S, 2.0)
    x_all = np.nan_to_num(S["model"])
    pose_all = np.nan_to_num(S["la_pose"].copy())
    act_all = np.nan_to_num(S["la_act"].copy())
    yaw_all = S["la_yaw"].copy()
    has_yaw = np.isfinite(yaw_all).mean() > 0.9
    yaw_std = float(np.nanstd(yaw_all))
    yaw_all = np.nan_to_num(yaw_all)
    ld = float(np.nanmedian(S["lat_delay"][m])) if np.isfinite(S["lat_delay"][m]).any() else 0.2
    LD = int(round(ld * FS))
    meanv = float(np.median(v[m]))
    del S
    R = V.runs(m, t, min_s=8.0)

    # --- per-route lag search, per band, per vbin, per channel (pose, yaw)
    lags = {}
    for bi, (f1, f2) in enumerate(BANDS):
        bb = {"x": [], "pose": [], "yaw": [], "act": [], "vb": []}
        for (i0, i1) in R:
            bb["x"].append(bp(x_all[i0:i1], f1, f2))
            bb["pose"].append(bp(pose_all[i0:i1], f1, f2))
            bb["yaw"].append(bp(yaw_all[i0:i1], f1, f2))
            bb["act"].append(bp(act_all[i0:i1], f1, f2))
            bb["vb"].append(vbin(v[i0:i1]))
        for ch in ("pose", "yaw", "act"):
            for k in range(len(VB)):
                c = np.zeros(MAXLAG + 1); e = np.zeros(MAXLAG + 1)
                for xr, yr, vr in zip(bb["x"], bb[ch], bb["vb"]):
                    n = len(xr)
                    if n < MAXLAG + 200 or not np.any(vr == k):
                        continue
                    mk = (vr == k).astype(float)
                    tr = int(0.5 / f1 * FS)
                    mk[:tr] = 0; mk[max(0, n - tr - MAXLAG):] = 0
                    if not np.any(mk):
                        continue
                    xk = xr * mk
                    cc = signal.correlate(yr, xk, mode="full", method="fft")
                    c += cc[n - 1: n + MAXLAG]
                    ee = signal.correlate(yr * yr, mk, mode="full", method="fft")
                    e += ee[n - 1: n + MAXLAG]
                lags[(bi, ch, k)] = int(np.argmax(c / np.sqrt(np.maximum(e, 1e-12)))) if np.any(c != 0) else LD
        del bb

    # --- per-sample reduced channels, decimated
    rec = {}
    for ri, (i0, i1) in enumerate(R):
        n = i1 - i0
        x = x_all[i0:i1]; p = pose_all[i0:i1]; y = yaw_all[i0:i1]; a = act_all[i0:i1]
        vb = vbin(v[i0:i1])
        idx = np.arange(0, n, DEC)
        chunk = ((t[i0:i1][idx] - t[i0]) // 60).astype(np.int32)
        R_ = dict(run=np.full(len(idx), ri, np.int32), chunk=chunk, v=v[i0:i1][idx].astype(np.float32),
                  vb=vb[idx].astype(np.int8))
        for bi, (f1, f2) in enumerate(BANDS):
            trim = int(0.5 / f1 * FS)
            valid = np.zeros(n, bool)
            if n > 2 * trim + MAXLAG + 50:
                valid[trim: n - trim - MAXLAG] = True
            xb = bp(x, f1, f2); pb = bp(p, f1, f2); yb = bp(y, f1, f2); ab = bp(a, f1, f2)
            env = np.abs(signal.hilbert(xb))
            ii = np.arange(n)

            def at(arr, Ls):
                return arr[np.minimum(ii + Ls, n - 1)]

            LperP = np.array([lags[(bi, "pose", k)] if k >= 0 else LD for k in vb])
            LperY = np.array([lags[(bi, "yaw", k)] if k >= 0 else LD for k in vb])
            LperA = np.array([lags[(bi, "act", k)] if k >= 0 else LD for k in vb])
            R_[f"b{bi}_x"] = xb[idx].astype(np.float32)
            R_[f"b{bi}_env"] = env[idx].astype(np.float32)
            R_[f"b{bi}_pL"] = at(pb, LperP)[idx].astype(np.float32)
            R_[f"b{bi}_pD"] = at(pb, np.full(n, LD))[idx].astype(np.float32)
            R_[f"b{bi}_yL"] = at(yb, LperY)[idx].astype(np.float32)
            R_[f"b{bi}_yD"] = at(yb, np.full(n, LD))[idx].astype(np.float32)
            R_[f"b{bi}_aL"] = at(ab, LperA)[idx].astype(np.float32)
            R_[f"b{bi}_aD"] = at(ab, np.full(n, LD))[idx].astype(np.float32)
            R_[f"b{bi}_valid"] = valid[idx]
        for k_, y_ in R_.items():
            rec.setdefault(k_, []).append(y_)
    out = {k: np.concatenate(v_) for k, v_ in rec.items()}
    np.savez_compressed(OUT / f"{route}.npz", **out,
                         meta=np.array(json.dumps(dict(route=route, group=V.ROUTES[route]["group"],
                                                        lat_delay=ld, meanv=meanv, has_yaw=bool(has_yaw),
                                                        yaw_std=yaw_std, nruns=len(R),
                                                        lags={f"{bi}_{c}_{k}": int(L) / FS for (bi, c, k), L in lags.items()}))))
    print(route, V.ROUTES[route]["group"], "runs", len(R), "ld", round(ld, 3), "meanv", round(meanv, 1),
          "has_yaw", has_yaw,
          {f"b{bi}{c}{k}": round(L / FS, 3) for (bi, c, k), L in lags.items()}, flush=True)


if __name__ == "__main__":
    for r in (sys.argv[1:] or ROUTES):
        main(r)
