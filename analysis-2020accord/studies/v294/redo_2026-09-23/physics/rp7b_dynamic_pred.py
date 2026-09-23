"""
Claim 6, real data, second pass: a DYNAMIC (byte-exact 1 kHz) feedforward predictor, a polarity leg from the data,
and a synthetic-LIVE positive control built on the same V293 routes.

 1. march the integer chain at 1 kHz on the route's own command (ZOH at 100 Hz, idx/sign/fade exactly as the flight
    read forms them), r26 = 0 (V293) -> pred_dyn; tap sampling instant scanned; residual_null = tap - pred_dyn.
 2. POLARITY LEG: in the tap's own sign convention, the torque must accelerate the wheel along its own sign at short
    lag (inertia) -> sign of corr(HP pred_dyn, HP d/dt(s * wire)) picks s = +1 or -1 (the x the trim sees).
 3. SYNTHETIC LIVE: march again WITH the V294 trim fed by x = s * wire (up-sampled to 1 kHz), quantise -> tap_live
    (open-loop: the wheel motion is the V293 drive's own; the test is whether the instrument recovers a known trim).
 4. estimators E1/E2/E3 on residual_null and residual_live; slope units T counts per deg/s^2 on R = -d/dt LPF(0x18F).
"""
import os, sys, math, io, contextlib
import numpy as np
from scipy import signal

os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/grind")
with contextlib.redirect_stdout(io.StringIO()):
    import v293_flight_read as FR
from rp7_v293_null import lp1

MAPX = (0, 12, 20, 24, 32, 64, 96, 128, 160, 240)
MAPY = (0, 52, 86, 103, 138, 275, 413, 550, 688, 1032)
LERP = np.array([int(np.interp(i, MAPX, MAPY)) for i in range(241)])


def march(sp_sign, idx, m, x1k=None, trim=False):
    """1 kHz integer march; sp_sign/idx/m are per 100 Hz frame (ZOH x10); x1k per tick. Returns T per tick."""
    n = len(idx) * 10
    T = np.zeros(n); s_fb = 0; o = 0
    for i in range(n):
        k = i // 10
        sp = int(sp_sign[k]) * int(LERP[int(idx[k])])
        r26 = 0
        if trim:
            x = int(max(-12000, min(12000, x1k[i])))
            s_new = ((1011 * s_fb) >> 10) + ((567 * x) >> 10)
            r26 = max(-1024, min(1024, s_new - s_fb)); s_fb = s_new
        P = max(-15360, min(15360, (((sp << 2) - r26) * 960) >> 8))
        S = max(-15360, min(15360, (int(m[k]) * P) >> 8))
        o2 = ((992 * o) >> 10) + ((S * 507) >> 10)
        y = (o + o2) >> 5; o = o2
        T[i] = max(-3072, min(3072, (y * 5346) >> 15))
    return T


def quant(T):
    return np.sign(T) * (np.abs(T).astype(np.int64) >> 3) * 8.0


def hp(x, fc, fs=100.0):
    b, a = signal.butter(2, fc / (fs / 2), "high")
    return signal.filtfilt(b, a, x)


def analyse(tag, win_s=20.0, maxlen_s=None):
    with contextlib.redirect_stdout(io.StringIO()):
        r = FR.load_route(tag, "V293")
    g, c = r.g, r.c
    t100 = g["t"]; n100 = len(t100)
    if maxlen_s:
        n100 = min(n100, int(maxlen_s * 100))
    fmode = "bar"
    m100 = FR.fade_multiplier(c, g["bar"], g["vego"], fmode)[:n100]
    idx100, sgn100 = FR.GI.demand_live(np.round(g["cmd"]), g["bar"], c)
    idx100 = np.clip(np.round(idx100[:n100]), 0, 240).astype(int)
    sgn = (-np.asarray(sgn100[:n100])).astype(int)                 # predict_tap's sign: T = -sgn * |T|
    Tn = march(sgn, idx100, m100)                                    # the null (V293) dynamic predictor
    # tap alignment: sample the 1 kHz march at t_tap + delta, delta scanned (ms)
    t_tap, T_tap = g["T_t"], g["T"]
    keep = (t_tap > t100[0]) & (t_tap < t100[n100 - 1])
    t_tap, T_tap = t_tap[keep], T_tap[keep]
    j100 = np.clip(np.searchsorted(t100[:n100], t_tap, side="right") - 1, 0, n100 - 1)
    sub = np.clip(np.round((t_tap - t100[j100]) * 1000).astype(int), 0, 9)
    tick_of = lambda tt, d: np.clip(10 * j100 + sub + d, 0, len(Tn) - 1)
    eng = g["eng"][:n100][j100] & (np.abs(g["bar"][:n100][j100]) < 400)
    best = None
    for d in range(-40, 61, 2):
        for sg in (+1, -1):
            res = T_tap - sg * quant(Tn[tick_of(t_tap, d)])
            v = np.var(res[eng])
            if best is None or v < best[0]:
                best = (v, d, sg)
    _, dms, sg = best
    ticks = tick_of(t_tap, dms)
    pred_dyn = sg * Tn[ticks]
    res_null = T_tap - pred_dyn
    # static predictor for comparison (the flight read's)
    pred100, _ = FR.predict_tap(c, idx100, np.asarray(sgn100[:n100]), m100)
    # ---- polarity leg ----
    wire = np.nan_to_num(g["wire"][:n100]) / 8.0
    ff100 = sg * Tn[::10][:n100]
    best_pol = None
    for s in (+1, -1):
        acc = np.gradient(lp1(s * wire, 15.0)) * 100
        a_, b_ = hp(ff100, 3.0), hp(acc, 3.0)
        cc = [np.corrcoef(a_[:-L or None][g["eng"][:n100][:-L or None]], b_[L:][g["eng"][:n100][:-L or None]])[0, 1] for L in range(0, 8)]
        pk = cc[int(np.argmax(np.abs(cc)))]
        if best_pol is None or pk > best_pol[1]:
            best_pol = (s, pk, int(np.argmax(np.abs(cc))))
    s_x, pol_c, pol_lag = best_pol
    # ---- synthetic live: the V294 trim fed by x = s_x * wire in the TAP convention (x_tapconv) ----
    x_up = signal.resample_poly(s_x * wire * 8.0, 10, 1)[:n100 * 10]
    Tl = march(sgn, idx100, m100, x1k=np.round(x_up), trim=True)
    tap_live = T_tap + sg * (quant(Tl[ticks]) - quant(Tn[ticks]))   # inject exactly the trim's delivered delta
    res_live = tap_live - pred_dyn
    # ---- regressors ----
    lr = lp1(wire, -math.log(1011 / 1024) / (2 * math.pi * 1e-3))
    R = -np.gradient(lr) * 100.0
    Rm = lp1(R, 5.05)
    dff = np.gradient(pred100) * 100.0
    bl = None
    for k in range(-4, 13):
        jj = np.clip(j100 + k, 0, n100 - 1)
        v = np.var((T_tap - pred100[jj])[eng])
        if bl is None or v < bl[0]:
            bl = (v, k)
    lag_s = bl[1]
    out = []
    mm = eng
    dd = np.diff(np.r_[0, mm.astype(int), 0])
    for a, b in zip(np.flatnonzero(dd == 1), np.flatnonzero(dd == -1)):
        nw = int(win_s * 50)
        for s0 in range(a, b - nw + 1, nw):
            sl = slice(s0 + 50, s0 + nw)
            jr = j100[sl]
            row = dict(v=float(np.mean(g["vego"][jr])), rate_rms=float(np.std(wire[jr])))
            # the AS-SPECIFIED instrument: static surface predictor at the identity's best lag, regressor R, no nuisance
            y_s = T_tap[sl] - pred100[np.clip(jr + lag_s, 0, n100 - 1)]
            X = np.column_stack([np.ones(len(y_s)), R[jr]])
            row["null_static_E1"] = float(np.linalg.lstsq(X, y_s, rcond=None)[0][1])
            X = np.column_stack([np.ones(len(y_s)), R[jr], pred100[np.clip(jr + lag_s, 0, n100 - 1)], dff[np.clip(jr + lag_s, 0, n100 - 1)]])
            row["null_static_E2"] = float(np.linalg.lstsq(X, y_s, rcond=None)[0][1])
            for nm, y in (("null_dyn", res_null[sl]), ("live_dyn", res_live[sl])):
                for en, cols in (("E1", [R[jr]]), ("E2", [R[jr], pred_dyn[sl], dff[jr]]), ("E3", [Rm[jr], pred_dyn[sl], dff[jr]])):
                    X = np.column_stack([np.ones(len(y))] + cols)
                    row[f"{nm}_{en}"] = float(np.linalg.lstsq(X, y, rcond=None)[0][1])
            out.append(row)
    return dict(tag=tag, dms=dms, sg=sg, s_x=s_x, pol_c=pol_c, pol_lag=pol_lag,
                resid_null=float(np.sqrt(np.mean(res_null[eng] ** 2))),
                resid_static=float(np.sqrt(np.mean((T_tap - pred100[np.clip(j100 + lag_s, 0, n100 - 1)])[eng] ** 2))), windows=out)


if __name__ == "__main__":
    tags = sys.argv[1:] or ["r70_v293", "r71_v293r2", "r72_v293r3", "r73_v293r3", "r75_v293r4"]
    allw = []
    for tag in tags:
        try:
            o = analyse(tag)
        except Exception as e:
            import traceback; traceback.print_exc()
            print(f"{tag}: FAILED {type(e).__name__}: {str(e)[:200]}"); continue
        W = o["windows"]; allw += W
        print(f"{tag}: tap delta {o['dms']} ms, tap sign {o['sg']:+d}; dynamic-pred resid {o['resid_null']:.1f} vs static {o['resid_static']:.1f} counts; "
              f"POLARITY: x_tapconv = {o['s_x']:+d} * wire (peak HP corr {o['pol_c']:+.2f} at {o['pol_lag']*10} ms); {len(W)} windows")
        if W:
            A = {k: np.array([w[k] for w in W]) for k in W[0]}
            for k in [k for k in A if k.startswith(("null", "live"))]:
                print(f"    {k:12s}: median {np.median(A[k]):+.3f}  5-95% [{np.percentile(A[k],5):+.3f}, {np.percentile(A[k],95):+.3f}]")
    if allw:
        A = {k: np.array([w[k] for w in allw]) for k in allw[0]}
        print(f"\nALL {len(allw)} windows:")
        for k in [k for k in A if k.startswith(("null", "live"))]:
            print(f"  {k:12s}: median {np.median(A[k]):+.3f}  5-95% [{np.percentile(A[k],5):+.3f}, {np.percentile(A[k],95):+.3f}]  "
                  f"frac>+0.05 {np.mean(A[k]>0.05):.2f}")
        for en in ("E1", "E2", "E3"):
            nl, lv = A[f"null_dyn_{en}"], A[f"live_dyn_{en}"]
            thr = 0.5 * np.median(lv)
            print(f"  {en}: separation -- live median {np.median(lv):+.3f}, null median {np.median(nl):+.3f}; with threshold {thr:+.3f}: "
                  f"live correct {np.mean(lv > thr):.2f}, null correct {np.mean(nl < thr):.2f}")
