"""
REDO-PHYSICS claim 6, REAL-DATA NULL CONTROL: V293 routes have NO trim (fb clamp 0 forces r26 = 0 on every path),
so the V294 instrument run on them MUST read zero. Anything else is the instrument's own confound.

Uses the kit's own V293 flight-read machinery (load_route, predict_tap with the best of three fade readings, the
identity's lag scan) so the residual is formed exactly as the V294 read would form it. Episodes = engaged, hands-off
(|bar| < 400) runs cut into 20 s windows.
  R     = -d/dt LPF_2.03Hz(0x18F rate)   (deg/s^2), the specified regressor ('-(0x18F rate, 2 Hz LPF, differenced)')
  E1    OLS residual ~ 1 + R                          (as specified)
  E2    OLS residual ~ 1 + R + FFpred + dFFpred/dt    (feedforward nuisance terms)
  E3    E2 with R through the 5 Hz output-lag replica
Reported in T counts per deg/s^2 (the live expectation below the pole is +0.21; the closed-loop sim gives 0.10-0.19).
"""
import os, sys, math, io, contextlib
import numpy as np

os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
HERE = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/grind"
sys.path.insert(0, HERE)
with contextlib.redirect_stdout(io.StringIO()):
    import v293_flight_read as FR


def lp1(xs, fc, fs=100.0):
    a = math.exp(-2 * math.pi * fc / fs); y = np.zeros_like(xs); s = xs[0]
    for i, v in enumerate(xs):
        s = a * s + (1 - a) * v; y[i] = s
    return y


def run(tag, build="V293", win_s=20.0):
    with contextlib.redirect_stdout(io.StringIO()):
        r = FR.load_route(tag, build)
    g, c = r.g, r.c
    t_tap, T_tap = g["T_t"], g["T"]
    j0 = np.searchsorted(g["t"], t_tap, side="right") - 1
    okj = (j0 >= 0) & (j0 < len(g["t"]))
    t_tap, T_tap, j0 = t_tap[okj], T_tap[okj], j0[okj]
    # choose the fade reading and lag exactly as the identity does (best R2 over the route)
    best = None
    for fmode in ("bar", "speed", "const"):
        m100 = FR.fade_multiplier(c, g["bar"], g["vego"], fmode)
        idx100, sgn100 = FR.GI.demand_live(np.round(g["cmd"]), g["bar"], c)
        pred100, _ = FR.predict_tap(c, np.round(idx100), sgn100, m100)
        # the signed predictor: orient it to the tap (the record: tap polarity +sign(cmd))
        for k in range(-4, 13):
            jj = np.clip(j0 + k, 0, len(g["t"]) - 1)
            sel = g["eng"][jj]
            if sel.sum() < 500:
                continue
            for sg in (+1, -1):
                res = T_tap[sel] - sg * pred100[jj[sel]]
                v = np.var(res)
                if best is None or v < best[0]:
                    best = (v, fmode, k, sg, pred100)
    _, fmode, lag, sg, pred100 = best
    pred = sg * pred100
    rate = g["wire"] / 8.0                                    # 0x18F, deg/s (raw sign)
    lr = lp1(np.nan_to_num(rate), -math.log(1011 / 1024) / (2 * math.pi * 1e-3))
    R = -np.gradient(lr) * 100.0
    Rm = lp1(R, 5.05)
    dff = np.gradient(pred) * 100.0
    jj = np.clip(j0 + lag, 0, len(g["t"]) - 1)
    res_all = T_tap - pred[jj]
    handsoff = (np.abs(g["bar"]) < 400)
    m = g["eng"][jj] & handsoff[jj]
    # episodes: contiguous runs of m (tap indices), cut into windows of win_s
    out = []
    d = np.diff(np.r_[0, m.astype(int), 0])
    for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
        n = int(win_s * 50)
        for s0 in range(a, b - n + 1, n):
            sl = slice(s0 + 50, s0 + n)                        # drop the first second of each window
            y = res_all[sl]; jr = j0[sl]
            def ols(cols):
                X = np.column_stack([np.ones(len(y))] + cols)
                bta, *_ = np.linalg.lstsq(X, y, rcond=None)
                return bta[1]
            e1 = ols([R[jr]]); e2 = ols([R[jr], pred[jj[sl]], dff[jj[sl]]]); e3 = ols([Rm[jr], pred[jj[sl]], dff[jj[sl]]])
            out.append(dict(v=float(np.nanmean(g["vego"][jr])), rate_rms=float(np.nanstd(rate[jr])),
                            R_rms=float(np.nanstd(R[jr])), resid=float(np.sqrt(np.mean(y ** 2))),
                            ff_rms=float(np.std(pred[jj[sl]])), E1=e1, E2=e2, E3=e3))
    return dict(tag=tag, fade=fmode, lag=lag, sign=sg, windows=out)


if __name__ == "__main__":
    tags = sys.argv[1:] or ["r70_v293", "r71_v293r2", "r72_v293r3", "r73_v293r3"]
    allw = []
    for tag in tags:
        try:
            o = run(tag)
        except Exception as e:
            print(f"{tag}: FAILED {type(e).__name__}: {str(e)[:160]}")
            continue
        W = o["windows"]; allw += W
        if not W:
            print(f"{tag}: no windows"); continue
        A = {k: np.array([w[k] for w in W]) for k in W[0]}
        print(f"{tag}: fade {o['fade']}, lag {o['lag']} fr, pred sign {o['sign']:+d}; {len(W)} x 20 s hands-off engaged windows; "
              f"median speed {np.median(A['v']):.1f}, rate rms {np.median(A['rate_rms']):.1f} deg/s, resid {np.median(A['resid']):.1f} counts")
        for e in ("E1", "E2", "E3"):
            x = A[e]
            print(f"    {e}: median {np.median(x):+.3f}  IQR [{np.percentile(x,25):+.3f}, {np.percentile(x,75):+.3f}]  "
                  f"5-95% [{np.percentile(x,5):+.3f}, {np.percentile(x,95):+.3f}]  frac > +0.05: {np.mean(x>0.05):.2f}  frac < -0.05: {np.mean(x<-0.05):.2f}")
    if allw:
        A = {k: np.array([w[k] for w in allw]) for k in allw[0]}
        print(f"\nALL {len(allw)} windows (V293 = a TRUE NULL):")
        for lo, hi in ((0, 8), (8, 15), (15, 40)):
            s = (A["v"] >= lo) & (A["v"] < hi)
            if s.sum() < 3: continue
            print(f"  speed {lo}-{hi} m/s ({s.sum()} windows):" + "".join(
                f"  {e} median {np.median(A[e][s]):+.3f} [5-95% {np.percentile(A[e][s],5):+.3f},{np.percentile(A[e][s],95):+.3f}]" for e in ("E1", "E2", "E3")))
        # the confound check: does E1 track the fade-model error? correlate E1 with ff_rms/R_rms (the leverage ratio)
        lev = A["ff_rms"] / np.maximum(A["R_rms"], 1e-6)
        print(f"  corr(E1, FF-to-R leverage) = {np.corrcoef(A['E1'], lev)[0,1]:+.2f};  corr(E2, leverage) = {np.corrcoef(A['E2'], lev)[0,1]:+.2f}")
