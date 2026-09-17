"""Independent re-derivation of the s1_goal 'lowspeed-excess-0p6-1p2hz-motion' finding.

Does NOT reuse s1_reduce.py / s1_analyze.py machinery (tercile-edge pooling, per-vbin cross-corr lag
tables, hilbert envelopes, etc). Loads the RAW caches directly through v282cmp.load(), band-passes with
plain zero-phase butterworth, aligns with a simple whole-run cross-correlation lag search (bounded to
+-0.8 s, same bound the original used), and computes:
  (a) rms(y_aligned - x) / rms(x)   -- the same 'relative error' definition as s1's rE_pD/rE_pL
  (b) rms(y_aligned) / rms(x)        -- the amplitude/motion ratio behind fig4
at 2-8 and 8-15 m/s in the 0.6-1.2 Hz band, both pooled ('all') and restricted to a simple top-third
amplitude split (envelope of the band-passed model, per-route quantile -- NOT the original's pooled
equal-group-weight quantile, to see if that methodological choice matters).

Also independently checks the 'steady large accel' claim: sign-folded secant gain of la_pose (lag
aligned on lat_delay) vs the 2.5 Hz lowpassed model, restricted to |model| >= 1 m/s^2, all speeds.

Uses la_pose as the primary achieved channel (independent of steering-ratio calibration, per v282cmp
docstring) and cross-checks against la_act.

Output: verify_results.json + a short printed table.
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

HERE = Path(__file__).resolve().parent
FS = V.FS

GROUPS_ROUTES = {
    "V282": ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"],
    "T64": ["0000006c--68c6e94b17", "0000006d--05e83bb04f"],
    "T64B": ["0000006e--6ca3e014fd"],
    "T5": ["00000076--d0b7ea7e4d"],
    "T4": ["00000075--6c8687d5bd"],
    "V282old": ["00000039--f56039af87", "0000003a--283a39a1d6", "0000003c--927965c2b4"],
}


def bp(x, f1, f2):
    sos = signal.butter(2, [f1, f2], btype="band", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x, padtype="even")


def best_lag(x, y, maxlag_s=0.8):
    """Whole-run normalised cross-correlation lag search, y[t+L] vs x[t], L in [0, maxlag]. Independent of
    s1_reduce's per-(route,speedbin) FFT-correlate machinery -- plain direct search here."""
    n = len(x)
    L = int(maxlag_s * FS)
    best, lag = -np.inf, 0
    xn = x - x.mean()
    for k in range(0, L + 1):
        xa = xn[: n - k]
        ya = y[k:] - y[k:].mean()
        if len(xa) < 50:
            break
        denom = np.sqrt(np.sum(xa * xa) * np.sum(ya * ya))
        if denom < 1e-9:
            continue
        c = float(np.dot(xa, ya)) / denom
        if c > best:
            best, lag = c, k
    return lag


def collect_band(route, f1, f2, vmin, vmax, ach_key="la_pose", lag_mode="best"):
    """Per usable run in [vmin,vmax): band-pass x=model and y=achieved, lag-align y to x, return
    concatenated (x_aligned, y_aligned, env) with edges trimmed.
    lag_mode='best': per-run best-lag search (bounded 0.8s) -- optimistic, checks the gain-limited case.
    lag_mode='fixed': shift by the ROUTE's median learned lat_delay (S['lat_delay']) -- the 'on schedule'
    metric the finding actually quotes (matches s1_reduce's _D channel definition)."""
    S = V.load(route)
    m = V.usable(S, vmin, vmax)
    t = S["t"]
    ld = float(np.nanmedian(S["lat_delay"][m])) if np.isfinite(S["lat_delay"][m]).any() else 0.2
    LD_fixed = int(round(ld * FS))
    xs, ys, envs = [], [], []
    for i0, i1 in V.runs(m, t, min_s=6.0):
        x = np.nan_to_num(S["model"][i0:i1])
        y = np.nan_to_num(S[ach_key][i0:i1])
        n = i1 - i0
        trim = int(0.5 / f1 * FS)
        if n < 2 * trim + int(0.8 * FS) + 50:
            continue
        xb = bp(x, f1, f2)
        yb = bp(y, f1, f2)
        lag = best_lag(xb, yb) if lag_mode == "best" else LD_fixed
        ya = yb[lag: lag + n] if lag == 0 else np.concatenate([yb[lag:], np.full(lag, yb[-1])])[:n]
        env = np.abs(signal.hilbert(xb))
        xs.append(xb[trim: n - trim])
        ys.append(ya[trim: n - trim])
        envs.append(env[trim: n - trim])
    del S
    if not xs:
        return None
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(envs)


def rel_err_ratio(x, y):
    return dict(rel_err=float(np.sqrt(np.mean((y - x) ** 2)) / max(np.sqrt(np.mean(x ** 2)), 1e-9)),
                rms_ratio=float(np.sqrt(np.mean(y ** 2)) / max(np.sqrt(np.mean(x ** 2)), 1e-9)),
                rho=float(np.corrcoef(x, y)[0, 1]) if len(x) > 10 else float("nan"),
                n=int(len(x)))


def group_band(group, f1, f2, vmin, vmax, ach_key="la_pose", top_third=False, lag_mode="best"):
    xs, ys = [], []
    per_route = []
    for r in GROUPS_ROUTES[group]:
        c = collect_band(r, f1, f2, vmin, vmax, ach_key, lag_mode=lag_mode)
        if c is None:
            continue
        x, y, env = c
        if top_third:
            if len(x) < 30:
                continue
            thr = np.quantile(env, 2 / 3)
            sel = env >= thr
            x, y = x[sel], y[sel]
        if len(x) < 30:
            continue
        xs.append(x); ys.append(y)
        per_route.append(dict(route=r, **rel_err_ratio(x, y)))
    if not xs:
        return None
    X, Y = np.concatenate(xs), np.concatenate(ys)
    pooled = rel_err_ratio(X, Y)
    # block bootstrap over ROUTES (each route resampled whole; matches the finding's "CIs over routes")
    rng = np.random.default_rng(0)
    boots = []
    # bootstrap over per-route arrays directly (already computed above, xs/ys aligned with per_route order)
    for _ in range(500):
        pick = rng.integers(0, len(xs), len(xs))
        xb = np.concatenate([xs[i] for i in pick])
        yb = np.concatenate([ys[i] for i in pick])
        boots.append(rel_err_ratio(xb, yb)["rel_err"])
    ci = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))] if len(xs) > 1 else [None, None]
    return dict(group=group, band=f"{f1}-{f2}", vb=f"{vmin}-{vmax}", ach=ach_key, top_third=top_third,
                nroutes=len(xs), sec=pooled["n"] / FS, rel_err=pooled["rel_err"], rel_err_ci=ci,
                rms_ratio=pooled["rms_ratio"], rho=pooled["rho"], per_route=per_route)


def steady_large_accel(group, thr=1.0):
    """Sign-folded secant gain, lowpass 2.5 Hz, |model| >= thr, lag-aligned on the route's learned
    lat_delay (matches s1's 'on schedule' definition for the level check)."""
    num = 0.0; den = 0.0; ns = 0
    for r in GROUPS_ROUTES[group]:
        S = V.load(r)
        m = V.usable(S, 0.0, 99.0)
        t = S["t"]
        ld = float(np.nanmedian(S["lat_delay"][m])) if np.isfinite(S["lat_delay"][m]).any() else 0.2
        LD = int(round(ld * FS))
        for i0, i1 in V.runs(m, t, min_s=3.0):
            x = np.nan_to_num(S["model"][i0:i1])
            y = np.nan_to_num(S["la_pose"][i0:i1])
            n = i1 - i0
            xl = V.lowpass(x, 2.5)
            yl = V.lowpass(y, 2.5)
            if n <= LD + 10:
                continue
            xl = xl[: n - LD]
            yl = yl[LD:]
            sel = np.abs(xl) >= thr
            if sel.sum() < 5:
                continue
            sg = np.sign(xl[sel])
            num += float(np.sum(yl[sel] * sg))
            den += float(np.sum(np.abs(xl[sel])))
            ns += int(sel.sum())
        del S
    if den < 1e-9:
        return None
    return dict(group=group, secant=num / den, n=ns)


def main():
    out = dict(band_cells=[], steady=[], null_control=[], fixed_lag=[])
    print("=== fixed-lag (on-schedule, route's learned lat_delay) -- matches the finding's quoted rE_pD ===", flush=True)
    for grp in ["V282", "T64", "T64B", "T5", "T4"]:
        for vlo, vhi, label in [(2, 8, "2-8"), (8, 15, "8-15")]:
            rf = group_band(grp, 0.6, 1.2, vlo, vhi, "la_pose", top_third=False, lag_mode="fixed")
            if rf:
                out["fixed_lag"].append(rf)
                print(f"{grp:6s} {label:5s} 0.6-1.2Hz FIXED-LAG rel_err={rf['rel_err']:.3f} ci={rf['rel_err_ci']} "
                      f"rms_ratio={rf['rms_ratio']:.3f} rho={rf['rho']:.3f} nroutes={rf['nroutes']} sec={rf['sec']:.0f}", flush=True)
    print("=== best-lag (per-run optimistic) ===", flush=True)
    for grp in ["V282", "T64", "T64B", "T5", "T4"]:
        for vlo, vhi, label in [(2, 8, "2-8"), (8, 15, "8-15")]:
            r = group_band(grp, 0.6, 1.2, vlo, vhi, "la_pose", top_third=False)
            if r:
                out["band_cells"].append(r)
                print(f"{grp:6s} {label:5s} 0.6-1.2Hz ALL   rel_err={r['rel_err']:.3f} ci={r['rel_err_ci']} "
                      f"rms_ratio={r['rms_ratio']:.3f} rho={r['rho']:.3f} nroutes={r['nroutes']} sec={r['sec']:.0f}", flush=True)
            r2 = group_band(grp, 0.6, 1.2, vlo, vhi, "la_pose", top_third=True)
            if r2:
                out["band_cells"].append(r2)
                print(f"{grp:6s} {label:5s} 0.6-1.2Hz TOP3  rel_err={r2['rel_err']:.3f} ci={r2['rel_err_ci']} "
                      f"rms_ratio={r2['rms_ratio']:.3f} rho={r2['rho']:.3f} nroutes={r2['nroutes']} sec={r2['sec']:.0f}", flush=True)
        # cross-check with la_act
        r3 = group_band(grp, 0.6, 1.2, 2, 8, "la_act", top_third=False)
        if r3:
            out["band_cells"].append(r3)
            print(f"{grp:6s} 2-8   0.6-1.2Hz ALL (la_act) rel_err={r3['rel_err']:.3f} rms_ratio={r3['rms_ratio']:.3f} rho={r3['rho']:.3f}", flush=True)

    for grp in ["V282", "T64", "T64B", "T5", "T4"]:
        s = steady_large_accel(grp, 1.0)
        if s:
            out["steady"].append(s)
            print(f"{grp:6s} steady |a|>=1 secant(pose)={s['secant']:.3f} n={s['n']}", flush=True)

    # null control: shift la_pose by half the route length, same pipeline, 2-8 m/s, T64
    print("--- null control (T64, achieved circularly shifted half-run, 2-8 m/s, 0.6-1.2Hz) ---", flush=True)
    for r in GROUPS_ROUTES["T64"]:
        S = V.load(r)
        m = V.usable(S, 2, 8)
        t = S["t"]
        for i0, i1 in V.runs(m, t, min_s=6.0):
            x = np.nan_to_num(S["model"][i0:i1])
            y = np.nan_to_num(S["la_pose"][i0:i1])
            n = i1 - i0
            if n < 400:
                continue
            yshift = np.roll(y, n // 2)
            xb = bp(x, 0.6, 1.2); yb = bp(yshift, 0.6, 1.2)
            trim = int(0.5 / 0.6 * FS)
            if n < 2 * trim + 50:
                continue
            xa, ya = xb[trim:n - trim], yb[trim:n - trim]
            rr = rel_err_ratio(xa, ya)
            out["null_control"].append(dict(route=r, dur_s=(n - 2 * trim) / FS, **rr))
            print(f"  {r} run {(n-2*trim)/FS:.0f}s rel_err={rr['rel_err']:.3f} rho={rr['rho']:.3f}", flush=True)
        del S

    json.dump(out, open(HERE / "verify_results.json", "w"), indent=1)
    print("wrote verify_results.json")


if __name__ == "__main__":
    main()
