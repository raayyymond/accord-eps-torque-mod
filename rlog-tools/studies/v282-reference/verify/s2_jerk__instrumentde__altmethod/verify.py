"""ALTMETHOD adversarial verification of finding instrument-defects-la-yaw-zero-event-metrics-lag-biased.

Claims to stress with DIFFERENT estimators than the original:
 (a) cs_yaw (carState.yawRate) is all zero -> la_yaw void.        ALT: check EVERY cached route, not just one.
 (b) la_act == cs_curv * v^2 (steering-angle-derived, not felt).  ALT: robust (Theil-Sen) slope + per-route,
     plus a LAGGED cross-correlation check (does allowing a small lag between la_act and curv*v^2 improve
     the fit materially -- if la_act were a genuinely independent SENSOR measurement filtered/lagged
     differently from the geometric curvature, a lag search should find a non-zero optimal lag and a
     residual with real structure. If it's a pure relabeling, lag=0 wins trivially and residual is ~0).
 (c) event_metrics' correlation-based lag search is biased toward 0 as true lag grows (shrinking overlap).
     ALT: an independent lag estimator that does NOT shrink the overlap -- fixed-window, zero-padded
     cross-correlation (np.correlate 'full', pick peak) -- on the SAME synthetic steps, and on REAL event
     windows pulled from the T64 routes (not synthetic).
 Also: recount steeringPressed contamination of low-speed high-jerk peaks with an ALTERNATIVE peak
 detector (prominence-based, no fixed height) to see if the contamination fraction is an artifact of the
 find_peaks(height=...) choice.

Run ONE route at a time, del before loading next (RAM constraint).
"""
import sys, json
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference")
import numpy as np
from scipy import signal
import v282cmp as V

OUT = {}

# ---------- (a) cs_yaw all-zero: check EVERY cached route ----------
print("=== (a) carState.yawRate nonzero fraction, ALL cached routes ===")
yaw_check = {}
for rk in V.ROUTES:
    f = V.CACHE / f"{rk}.npz"
    if not f.exists():
        continue
    D = np.load(f, allow_pickle=True)
    if "cs_yaw" not in D.files or len(D["cs_yaw"]) == 0:
        yaw_check[rk] = dict(n=0, nonzero_frac=None, maxabs=None)
        print(f"  {rk:24s} NO cs_yaw FIELD / empty")
        continue
    cy = np.asarray(D["cs_yaw"])
    nz = float(np.mean(cy != 0.0))
    yaw_check[rk] = dict(n=int(len(cy)), nonzero_frac=nz, maxabs=float(np.max(np.abs(cy))))
    print(f"  {rk:24s} n={len(cy):7d}  nonzero_frac={nz:.4f}  max|yawRate|={np.max(np.abs(cy)):.4f}")
    del D, cy
OUT["yaw_check_all_routes"] = yaw_check

# ---------- (b) la_act vs curvature*v^2: robust regression + lag search, per route ----------
print("\n=== (b) la_act vs cs_curv*v^2: Theil-Sen slope + optimal-lag cross-corr, per route ===")


def theil_sen_slope(x, y, n_sub=4000, rng=None):
    rng = rng or np.random.default_rng(0)
    n = len(x)
    if n < 2:
        return float("nan")
    idx = rng.integers(0, n, size=(n_sub, 2))
    idx = idx[idx[:, 0] != idx[:, 1]]
    dx = x[idx[:, 1]] - x[idx[:, 0]]
    dy = y[idx[:, 1]] - y[idx[:, 0]]
    ok = np.abs(dx) > 1e-6
    return float(np.median(dy[ok] / dx[ok]))


b_check = {}
for rk in ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "00000064--ce6b0b0ebb", "0000006c--2bc842dbac"]:
    f = V.CACHE / f"{rk}.npz"
    if not f.exists():
        continue
    S = V.load(rk)
    D = np.load(f, allow_pickle=True)
    v = S["v"]
    curv_v2 = np.nan_to_num(D["cs_curv"]) * v * v if "cs_curv" in D.files and len(D["cs_curv"]) else None
    if curv_v2 is None or len(D["cs_curv"]) != len(S["t"]):
        # cs_curv is on the controlsState clock already (same length as t_cs / la_act), no interp needed
        curv_v2 = np.nan_to_num(D["cs_curv"]) * S["v"] * S["v"] if "cs_curv" in D.files else None
    m = V.usable(S) & np.isfinite(S["la_act"]) & (curv_v2 is not None)
    x = curv_v2[m] if curv_v2 is not None else np.array([])
    y = S["la_act"][m]
    if len(x) < 100:
        b_check[rk] = dict(note="insufficient data")
        del S, D
        continue
    corr = float(np.corrcoef(x, y)[0, 1])
    slope_ols = float(np.polyfit(x, y, 1)[0])
    slope_ts = theil_sen_slope(x, y)
    resid = y - slope_ols * x
    resid_rms = float(np.sqrt(np.mean(resid ** 2)))
    y_rms = float(np.sqrt(np.mean(y ** 2)))
    # lag search: does shifting la_act relative to curv*v^2 improve correlation? (independent sensor -> nonzero optimal lag)
    best_lag, best_corr = 0, corr
    xa_full, ya_full = x, y
    # use contiguous run for lag search (need ordered samples); take usable runs
    for a, bnd in V.runs(m, S["t"], min_s=5.0)[:5]:
        xs = curv_v2[a:bnd]; ys = S["la_act"][a:bnd]
        if len(xs) < 200:
            continue
        xs = xs - xs.mean(); ys = ys - ys.mean()
        c = signal.correlate(ys, xs, mode="full")
        lags = signal.correlation_lags(len(ys), len(xs), mode="full")
        k = np.argmax(np.abs(c))
        lag_samples = lags[k]
        norm = np.sqrt(np.sum(xs ** 2) * np.sum(ys ** 2))
        cc = c[k] / max(norm, 1e-9)
        if abs(cc) > abs(best_corr):
            best_corr, best_lag = float(cc), int(lag_samples)
    b_check[rk] = dict(corr=corr, slope_ols=slope_ols, slope_theilsen=slope_ts,
                        resid_rms=resid_rms, y_rms=y_rms, resid_over_y=resid_rms / max(y_rms, 1e-9),
                        best_lag_samples_one_run=best_lag, best_lag_corr_one_run=best_corr)
    print(f"  {rk:24s} corr={corr:.5f} slope_ols={slope_ols:.4f} slope_TS={slope_ts:.4f} "
          f"resid/y_rms={resid_rms/max(y_rms,1e-9):.4f} best_lag(samples,one run)={best_lag} (corr {best_corr:.4f})")
    del S, D, x, y
OUT["b_check"] = b_check

# ---------- (c) event_metrics lag bias: alt fixed-window zero-pad cross-corr estimator ----------
print("\n=== (c) synthetic step lag recovery: original (event_metrics) vs ALT fixed-window xcorr ===")


def alt_lag_estimator(x, y, fs=100.0, maxlag_s=0.8):
    """Zero-padded full cross-correlation; overlap does NOT shrink with lag (whole series correlated)."""
    xs = x - x.mean(); ys = y - y.mean()
    c = signal.correlate(ys, xs, mode="full")
    lags = signal.correlation_lags(len(ys), len(xs), mode="full")
    Lmax = int(maxlag_s * fs)
    sel = (lags >= 0) & (lags <= Lmax)
    k = np.argmax(c[sel])
    lag_samples = lags[sel][k]
    xa, ya = xs[: len(xs) - lag_samples] if lag_samples > 0 else xs, ys[lag_samples:] if lag_samples > 0 else ys
    gain = float(np.dot(xa, ya) / max(np.dot(xa, xa), 1e-9)) if len(xa) else float("nan")
    return lag_samples / fs, gain


c_check = {}
t = np.arange(0, 60, 1 / 100.0)
rng = np.random.default_rng(0)
x = V.lowpass(rng.standard_normal(len(t)), 0.8) * 3
for true_lag_s, true_gain in [(0.10, 0.9), (0.25, 0.9), (0.40, 0.9), (0.60, 0.9)]:
    lagN = int(true_lag_s * 100)
    y = true_gain * np.concatenate([np.zeros(lagN), x[:-lagN]]) if lagN > 0 else true_gain * x
    S = dict(model=x, la_act=y)
    em = V.event_metrics(S, 500, 5500, maxlag_s=0.8)
    alt_lag, alt_gain = alt_lag_estimator(x[500:5500], y[500:5500], maxlag_s=0.8)
    c_check[f"true_lag_{true_lag_s}"] = dict(true_lag=true_lag_s, true_gain=true_gain,
                                              orig_lag=em["lag"], orig_gain=em["gain"],
                                              alt_lag=float(alt_lag), alt_gain=float(alt_gain))
    print(f"  true_lag={true_lag_s:.2f}s  orig(event_metrics): lag={em['lag']:.3f} gain={em['gain']:.3f}  "
          f"ALT(fixed-window xcorr): lag={alt_lag:.3f} gain={alt_gain:.3f}")
OUT["c_check_synthetic"] = c_check

# ---------- (c2) real T64 event windows: orig vs alt lag estimator ----------
print("\n=== (c2) REAL T64 jerk-event windows: orig event_metrics lag vs ALT fixed-window xcorr lag ===")
c2_check = {}
for rk in ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]:
    f = V.CACHE / f"{rk}.npz"
    if not f.exists():
        continue
    S = V.load(rk)
    ev, j = V.jerk_events(S, jerk_thr=0.5, vmin=5.0)
    rows = []
    for e in ev:
        k = e["idx"]; a, b = k - 150, k + 300
        if a < 0 or b >= len(S["t"]):
            continue
        em = V.event_metrics(S, a, b, maxlag_s=0.8)
        x = np.nan_to_num(S["model"][a:b]); y = np.nan_to_num(S["la_act"][a:b])
        alt_lag, alt_gain = alt_lag_estimator(x, y, maxlag_s=0.8)
        rows.append(dict(t=e["t"], v=e["v"], orig_lag=em["lag"], orig_gain=em["gain"],
                          alt_lag=float(alt_lag), alt_gain=float(alt_gain)))
    c2_check[rk] = rows
    if rows:
        ol = np.array([r["orig_lag"] for r in rows]); al = np.array([r["alt_lag"] for r in rows])
        print(f"  {rk:24s} n_events={len(rows):3d}  median orig_lag={np.median(ol):.3f}  median alt_lag={np.median(al):.3f}")
    del S, ev, j
OUT["c2_check_real_events"] = c2_check

# ---------- steeringPressed contamination recheck with alt peak detector (prominence-based) ----------
print("\n=== steeringPressed contamination of low-speed high-jerk peaks: ALT prominence-based detector ===")
press_check = {}
for rk in ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac", "0000006c--68c6e94b17", "0000006d--05e83bb04f"]:
    f = V.CACHE / f"{rk}.npz"
    if not f.exists():
        continue
    S = V.load(rk)
    m = V.usable(S, 0, 8.0)
    model = np.nan_to_num(S["model"])
    jj = V.deriv(V.lowpass(model, 2.0))
    aj = np.abs(jj)
    # ALT: prominence-based peak find instead of fixed height threshold
    pk, props = signal.find_peaks(aj, prominence=0.4, distance=int(2.0 * V.FS))
    pk = [k for k in pk if m[k]]
    pressed_frac = float(np.mean(S["pressed"][pk])) if pk else float("nan")
    press_check[rk] = dict(n_peaks=len(pk), n_pressed=int(np.sum(S["pressed"][pk])) if pk else 0,
                            pressed_frac=pressed_frac)
    print(f"  {rk:24s} ALT(prominence) n_peaks(<8m/s)={len(pk):3d}  pressed={int(np.sum(S['pressed'][pk])) if pk else 0:3d}  frac={pressed_frac}")
    del S, model, jj, aj
OUT["pressed_contamination_altmethod"] = press_check

with open(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s2_jerk__instrumentde__altmethod/results.json", "w") as fh:
    json.dump(OUT, fh, indent=2, default=str)
print("\nWROTE results.json")
