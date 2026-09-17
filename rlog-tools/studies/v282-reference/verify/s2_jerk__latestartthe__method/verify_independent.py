"""Independent re-derivation of s2_jerk's headline numbers, bypassing s2_extract/s2_analyze/s2_common.
Recomputes jerk events, gain and 0-0.2s / 1.5-2.5s error directly from V.load() + V.jerk_events(), using a
plain cross-correlation lag + OLS gain (not the pipeline's fixed_lag), to check the magnitude survives an
independently-written estimator. One route in RAM at a time.
"""
import sys, json
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

THR, VMIN, PRE, POST = 0.4, 3.0, 1.0, 2.5
FS = V.FS
NPRE, NPOST = int(PRE*FS), int(POST*FS)

V282_ROUTES = [rk for rk, m in V.ROUTES.items() if m['group'] == 'V282']
T64_ROUTES = [rk for rk, m in V.ROUTES.items() if m['group'] == 'T64']


def simple_lag_gain(x, y, lo=-80, hi=80):
    """Plain integer-lag cross-correlation + OLS gain at best lag, independently written (no shared code
    with s2_extract.fixed_lag). y[k] ~ gain * x[k-lag]. Positive lag = achieved lags the model."""
    n = len(x)
    best_c, best_L = -2, 0
    for L in range(lo, hi+1):
        if L >= 0:
            xs, ys = x[:n-L] if L > 0 else x, y[L:]
        else:
            xs, ys = x[-L:], y[:n+L]
        if len(xs) < 30:
            continue
        xs = xs - xs.mean(); ys = ys - ys.mean()
        den = np.sqrt(np.sum(xs**2) * np.sum(ys**2))
        c = np.sum(xs*ys) / den if den > 0 else 0
        if c > best_c:
            best_c, best_L = c, L
    L = best_L
    if L >= 0:
        xs, ys = x[:n-L] if L > 0 else x, y[L:]
    else:
        xs, ys = x[-L:], y[:n+L]
    gain = np.sum(xs*ys) / max(np.sum(xs**2), 1e-9)
    return L/FS, gain, best_c


def collect_events(routes, vmin_strat=15.0):
    out = []
    for rk in routes:
        S = V.load(rk)
        ev, j = V.jerk_events(S, jerk_thr=THR, vmin=VMIN, pre=PRE, post=POST, min_sep=2.0)
        mlp = V.lowpass(np.nan_to_num(S['model']), 2.0)
        alp = V.lowpass(np.nan_to_num(S['la_act']), 3.0)
        sa = np.nan_to_num(S['sa'])
        for e in ev:
            k = e['idx']
            if e['v'] < vmin_strat:
                continue
            i0, i1 = k - NPRE, k + NPOST
            if i0 - 100 < 0 or i1 + 100 > len(mlp):
                continue
            a0 = float(np.mean(mlp[k-100:k-60])); a1 = float(np.mean(mlp[k+60:k+100]))
            D = abs(a1 - a0)
            if D < 0.2:
                continue
            dsign = np.sign(a1 - a0) if a1 != a0 else np.sign(e['jerk_peak'])
            L, gain, corr = simple_lag_gain(mlp[i0:i1], alp[i0:i1])
            base_m = np.mean(mlp[k-100:k-60]); base_a = np.mean(alp[k-100:k-60])
            mn = dsign * (mlp[i0:i1] - base_m) / D
            yn = dsign * (alp[i0:i1] - base_a) / D
            err_0_20 = float(np.mean((yn - mn)[NPRE:NPRE+20]))      # signed bias, 0-0.2s
            err_150_300 = float(np.mean((yn - mn)[NPRE+150:NPRE+300]))  # signed bias, 1.5-2.5s (clipped by array len)
            out.append(dict(route=rk, v=e['v'], jerk=abs(e['jerk_peak']), step=D, lag=L, gain=gain, corr=corr,
                             bias_0_20=err_0_20, bias_150_300=err_150_300))
        del S, ev, j, mlp, alp, sa
    return out


ref = collect_events(V282_ROUTES)
tq = collect_events(T64_ROUTES)

def med(rows, k):
    v = [r[k] for r in rows]
    return float(np.median(v)), len(v)

print("=== independent re-derivation (plain xcorr lag + OLS gain, no shared code with s2_extract/s2_common) ===")
for k in ('lag', 'gain', 'bias_0_20', 'bias_150_300'):
    rm, rn = med(ref, k); tm, tn = med(tq, k)
    print(f"{k:14s} V282 med={rm:+.3f} (n={rn})   T64 med={tm:+.3f} (n={tn})   raw diff={tm-rm:+.3f}")

json.dump(dict(ref=ref, tq=tq), open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s2_jerk__latestartthe__method/indep_events.json', 'w'), default=float)
