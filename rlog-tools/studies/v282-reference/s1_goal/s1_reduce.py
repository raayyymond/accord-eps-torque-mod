"""s1_goal pass 1: reduce each route to band-limited, lag-aligned tracking channels (one route in RAM at a time).

Reference x = MODEL desired lateral accel (cs_des_curv * v^2), per v282cmp.load.
Achieved channels:
  act  = controlsState actualLateralAccel (angle -> VehicleModel curvature * v^2; depends on liveParameters sR,
         which is 12.5 on V282old, 16.33 on V282, 16.84-16.88 on V293 routes -> NOT comparable across groups)
  pose = livePose yaw rate * v (independent of steering geometry; the primary cross-group measure)
  ctrl = x delayed by exactly 0.30 s (delay control: lag estimator must return 0.30, aligned gain 1.000)
  null = act circularly shifted by half its run (negative control: gain ~ 0)
For each band (zero-phase butter bandpass, whole run, edges trimmed 0.5/f_lo) the channel is sampled at
  _L : the lag measured for that route x speed bin x channel (max NORMALISED 0.15-1.2 Hz x-corr, 0..0.8 s)
  _D : the route's median learned lateral delay (lat_delay) -- the 'on schedule' comparison
and decimated x4 (bands <= 2.5 Hz).  Also per-band spectra (fixed nperseg) per speed-bin segment for the
band_H-equivalent cross-check with a run bootstrap.
out: s1_goal/_red/<route>.npz   (regenerable)
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

OUT = Path(__file__).resolve().parent / "_red"; OUT.mkdir(exist_ok=True)
FS = V.FS
BANDS = [(0.05, 0.15), (0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.50)]
NPS = [4096, 2048, 1024, 512, 256]
VB = [(2.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 99.0)]
DEC = 4
MAXLAG = int(0.8 * FS)


def bp(x, f1, f2):
    sos = signal.butter(2, [f1, f2], btype="band", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x, padtype="even")


def vbin(v):
    b = np.full(len(v), -1, int)
    for k, (a, c) in enumerate(VB):
        b[(v >= a) & (v < c)] = k
    return b


def shift(y, L):
    """y[t+L] with edge hold (the trimmed-valid mask removes edges)."""
    if L == 0:
        return y.copy()
    return np.concatenate([y[L:], np.full(L, y[-1])])


def main(route):
    S = V.load(route)
    t, v = S["t"], S["v"]
    m = V.usable(S, 2.0)
    x_all = np.nan_to_num(S["model"])
    act_all = np.nan_to_num(S["la_act"])
    pose_all = S["la_pose"].copy()
    has_pose = np.isfinite(pose_all).mean() > 0.9
    pose_all = np.nan_to_num(pose_all)
    ld = float(np.nanmedian(S["lat_delay"][m])) if np.isfinite(S["lat_delay"][m]).any() else 0.2
    sR = float(np.nanmedian(S["sR"][m]))
    del S
    LD = int(round(ld * FS))
    R = runs = V.runs(m, t, min_s=8.0)
    # --- lag per speed bin per channel from broadband 0.05-1.2 Hz
    xc = {}; bb = {}
    for (i0, i1) in runs:
        x = x_all[i0:i1]
        ctrl = np.concatenate([np.full(30, x[0]), x[:-30]])
        bb.setdefault("x", []).append(bp(x, 0.15, 1.2))
        bb.setdefault("act", []).append(bp(act_all[i0:i1], 0.15, 1.2))
        bb.setdefault("pose", []).append(bp(pose_all[i0:i1], 0.15, 1.2))
        bb.setdefault("ctrl", []).append(bp(ctrl, 0.15, 1.2))
        bb.setdefault("vb", []).append(vbin(v[i0:i1]))
    lags = {}
    for ch in ("act", "pose", "ctrl"):
        for k in range(len(VB)):
            c = np.zeros(MAXLAG + 1); e = np.zeros(MAXLAG + 1)
            for xr, yr, vr in zip(bb["x"], bb[ch], bb["vb"]):
                n = len(xr)
                if n < MAXLAG + 200 or not np.any(vr == k):
                    continue
                mk = (vr == k).astype(float); tr = int(0.5 / 0.15 * FS)
                mk[:tr] = 0; mk[max(0, n - tr - MAXLAG):] = 0
                xk = xr * mk
                cc = signal.correlate(yr, xk, mode="full", method="fft")   # cc[n-1+L] = sum_t y[t+L] xk[t]
                c += cc[n - 1: n + MAXLAG]
                ee = signal.correlate(yr * yr, mk, mode="full", method="fft")
                e += ee[n - 1: n + MAXLAG]
            lags[(ch, k)] = int(np.argmax(c / np.sqrt(np.maximum(e, 1e-12)))) if np.any(c != 0) else LD
    del bb
    # --- per-band reduced channels
    rec = {}
    specs = []   # (band, vbin, runid, dict of in-band Pxx,Pyy_act,Pxy_act,Pyy_pose,Pxy_pose, Pyy_ctrl, Pxy_ctrl, nsamp)
    for ri, (i0, i1) in enumerate(runs):
        n = i1 - i0
        x = x_all[i0:i1]; a = act_all[i0:i1]; p = pose_all[i0:i1]
        ctrl = np.concatenate([np.full(30, x[0]), x[:-30]])
        vb = vbin(v[i0:i1])
        idx = np.arange(0, n, DEC)
        R_ = dict(route=np.full(len(idx), 0, np.int16), run=np.full(len(idx), ri, np.int32),
                  chunk=((t[i0:i1][idx] - t[i0]) // 60).astype(np.int32), v=v[i0:i1][idx].astype(np.float32),
                  vb=vb[idx].astype(np.int8), t=(t[i0:i1][idx] - t[0]).astype(np.float32))
        Lper = lambda ch: np.array([lags[(ch, k)] if k >= 0 else LD for k in vb])
        for bi, (f1, f2) in enumerate(BANDS):
            trim = int(0.5 / f1 * FS)
            valid = np.zeros(n, bool)
            if n > 2 * trim + MAXLAG + 50:
                valid[trim: n - trim - MAXLAG] = True
            xb = bp(x, f1, f2); ab = bp(a, f1, f2); pb = bp(p, f1, f2); cb = bp(ctrl, f1, f2)
            env = np.abs(signal.hilbert(xb))
            ii = np.arange(n)
            def at(y, Ls):
                return y[np.minimum(ii + Ls, n - 1)]
            ch = dict(x=xb, env=env,
                      aL=at(ab, Lper("act")), aD=at(ab, np.full(n, LD)), a0=ab,
                      pL=at(pb, Lper("pose")), pD=at(pb, np.full(n, LD)),
                      cL=at(cb, Lper("ctrl")),
                      nul=np.roll(ab, n // 2))
            for k_, y in ch.items():
                R_[f"b{bi}_{k_}"] = y[idx].astype(np.float32)
            R_[f"b{bi}_valid"] = valid[idx]
        # broadband lowpassed (0-2.5 Hz) level channels for the binned nonlinear regression
        xl = V.lowpass(x, 2.5); al = V.lowpass(a, 2.5); pl = V.lowpass(p, 2.5)
        ii = np.arange(n)
        R_["lx"] = xl[idx].astype(np.float32)
        R_["laL"] = al[np.minimum(ii + Lper("act"), n - 1)][idx].astype(np.float32)
        R_["lpL"] = pl[np.minimum(ii + Lper("pose"), n - 1)][idx].astype(np.float32)
        vld = np.zeros(n, bool); vld[: n - MAXLAG] = True
        R_["l_valid"] = vld[idx]
        for k_, y in R_.items():
            rec.setdefault(k_, []).append(y)
        # spectra per speed bin sub-run
        for k in range(len(VB)):
            for (j0, j1) in V.runs(vb == k, t[i0:i1], min_s=0):
                seg = slice(j0, j1)
                for bi, (f1, f2) in enumerate(BANDS):
                    nps = NPS[bi]
                    if j1 - j0 < nps:
                        continue
                    def sp(u, w):
                        u = u - u.mean(); w = w - w.mean()
                        f, P = signal.csd(u, w, FS, nperseg=nps, noverlap=nps // 2)
                        return f, P
                    f, Pxx = sp(x[seg], x[seg])
                    s = (f >= f1) & (f < f2)
                    d = dict(Pxx=Pxx[s].real)
                    for nm, y in (("act", a), ("pose", p), ("ctrl", ctrl)):
                        _, Pyy = sp(y[seg], y[seg]); _, Pxy = sp(x[seg], y[seg])
                        d["Pyy_" + nm] = Pyy[s].real; d["Pxy_" + nm] = Pxy[s]
                    specs.append(dict(band=bi, vb=k, run=ri, n=j1 - j0, **d))
    out = {k: np.concatenate(v_) for k, v_ in rec.items()}
    np.savez_compressed(OUT / f"{route}.npz", **out,
                        specs=np.array(specs, dtype=object),
                        meta=np.array(json.dumps(dict(route=route, group=V.ROUTES[route]["group"], lat_delay=ld, sR=sR,
                                                       has_pose=bool(has_pose), nruns=len(runs),
                                                       lags={f"{c}_{k}": int(L) for (c, k), L in lags.items()}))))
    print(route, V.ROUTES[route]["group"], "runs", len(runs), "ld", round(ld, 3), "sR", sR, "pose", has_pose,
          {f"{c}{k}": L / FS for (c, k), L in lags.items()}, flush=True)


if __name__ == "__main__":
    for r in (sys.argv[1:] or list(V.ROUTES)):
        main(r)
