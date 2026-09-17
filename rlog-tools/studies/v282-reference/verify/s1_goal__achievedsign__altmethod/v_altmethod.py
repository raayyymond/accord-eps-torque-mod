"""Adversarial verify of finding s1_goal/achieved-signal-crosscheck (ALTMETHOD lens).

Independently confirm/refute using estimators DIFFERENT from the original band_H spectral pass:
  1. la_yaw identically-zero check (trivial, but load raw and confirm on every cached route).
  2. TIME-DOMAIN lag-aligned OLS gain (event_metrics, ach_key='la_pose' vs 'la_act') on band-passed
     signals, restricted to sustained high-demand EVENTS (accel_events, nonlinear amplitude gate) rather
     than the whole-run Welch/csd spectral ratio the finding used. This is genuinely different: time
     domain vs frequency domain, event-gated vs continuous, robust median vs power-weighted mean.
  3. TAIL comparison: 90th-percentile |la_pose|/|model| envelope ratio vs the MEAN/H-based ratio, in the
     0.6-1.2 and 1.2-2.5 Hz "floor" bands, to see if the claimed floor is a mean-only artifact.
One route in RAM at a time; results cached to JSON.
"""
import sys, json, gc
from pathlib import Path
import numpy as np
from scipy import signal

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

OUT = Path(__file__).resolve().parent
FS = V.FS
BANDS = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.50)]


def bp(x, f1, f2):
    sos = signal.butter(2, [f1, f2], btype="band", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x, padtype="even")


def part1_layaw_zero():
    res = {}
    for rk in V.ROUTES:
        f = V.CACHE / f"{rk}.npz"
        if not f.exists():
            continue
        S = V.load(rk)
        m = V.usable(S, 0.0)
        yaw = S["la_yaw"]
        res[rk] = dict(std_all=float(np.nanstd(yaw)), std_usable=float(np.nanstd(yaw[m])),
                        nnan=int(np.isnan(yaw).sum()), n=len(yaw),
                        max_abs=float(np.nanmax(np.abs(yaw))) if np.isfinite(yaw).any() else None)
        del S
        gc.collect()
    return res


def part2_event_gain(rk, meta):
    """Time-domain event-gated gain: for each accel_event (|model|>=1.5, >=1s hold, >15 m/s slice),
    band-pass model/act/pose in each band over the padded event window, take lag-aligned OLS gain
    (event_metrics' own regression) restricted to that single event -- nonlinear (amplitude-gated),
    event-based (not continuous Welch), robust (median across events, not power-weighted mean)."""
    S = V.load(rk)
    evs = V.accel_events(S, la_thr=1.5, vmin=15.0, min_hold=1.0, pre=1.0, post=1.0)
    out = {b: dict(act=[], pose=[]) for b in range(len(BANDS))}
    for ev in evs:
        i0, i1 = ev["i0"], ev["i1"]
        if i1 - i0 < 64:
            continue
        for bi, (f1, f2) in enumerate(BANDS):
            n = i1 - i0
            if n < 6.0 / f1 * FS / 4:  # need a few cycles of the low edge
                continue
            x = bp(np.nan_to_num(S["model"][i0:i1]), f1, f2)
            a = bp(np.nan_to_num(S["la_act"][i0:i1]), f1, f2)
            p = bp(np.nan_to_num(S["la_pose"][i0:i1]), f1, f2)
            Ssub = dict(model=x, la_act=a, la_pose=p)
            try:
                ea = V.event_metrics(Ssub, 0, n, ach_key="la_act", maxlag_s=0.5)
                ep = V.event_metrics(Ssub, 0, n, ach_key="la_pose", maxlag_s=0.5)
            except Exception:
                continue
            if np.isfinite(ea["gain"]) and abs(ea["gain"]) < 20:
                out[bi]["act"].append(ea["gain"])
            if np.isfinite(ep["gain"]) and abs(ep["gain"]) < 20:
                out[bi]["pose"].append(ep["gain"])
    del S
    gc.collect()
    res = {}
    for bi in out:
        a, p = out[bi]["act"], out[bi]["pose"]
        res[bi] = dict(n_events=len(a), act_median=float(np.median(a)) if a else None,
                        act_p25=float(np.percentile(a, 25)) if a else None,
                        act_p75=float(np.percentile(a, 75)) if a else None,
                        pose_median=float(np.median(p)) if p else None,
                        pose_p25=float(np.percentile(p, 25)) if p else None,
                        pose_p75=float(np.percentile(p, 75)) if p else None)
    return dict(route=rk, group=meta["group"], n_events_total=len(evs), bands=res)


def part3_tail_vs_mean(rk, meta, vmin=15.0, pgate=0.05):
    """Envelope-ratio TAIL (p90 of |pose|/|model| over 1s windows, model-power-gated) vs the H mean,
    in the two 'floor' bands, at >vmin m/s. Different statistic: ratio-of-envelopes, windowed percentile,
    not a Welch cross-spectrum ratio."""
    S = V.load(rk)
    m = V.usable(S, vmin)
    x_all = np.nan_to_num(S["model"]); p_all = np.nan_to_num(S["la_pose"]); a_all = np.nan_to_num(S["la_act"])
    res = {}
    for bi, (f1, f2) in enumerate(BANDS):
        if bi < 2:
            continue  # only the two 'floor' bands 0.6-1.2, 1.2-2.5
        xb = bp(x_all, f1, f2); pb = bp(p_all, f1, f2); ab = bp(a_all, f1, f2)
        win = int(1.0 * FS)
        ratios_p, ratios_a, meanH_num_p, meanH_num_a, meanH_den = [], [], 0.0, 0.0, 0.0
        for i in range(0, len(xb) - win, win):
            if not m[i:i + win].all():
                continue
            xe = np.sqrt(np.mean(xb[i:i + win] ** 2))
            if xe < pgate:
                continue
            pe = np.sqrt(np.mean(pb[i:i + win] ** 2))
            ae = np.sqrt(np.mean(ab[i:i + win] ** 2))
            ratios_p.append(pe / xe); ratios_a.append(ae / xe)
            meanH_num_p += pe * xe; meanH_num_a += ae * xe; meanH_den += xe * xe
        if len(ratios_p) < 5:
            continue
        res[bi] = dict(n_win=len(ratios_p),
                        pose_mean_ratio=float(np.mean(ratios_p)), pose_p90=float(np.percentile(ratios_p, 90)),
                        pose_median=float(np.median(ratios_p)),
                        act_mean_ratio=float(np.mean(ratios_a)), act_p90=float(np.percentile(ratios_a, 90)),
                        act_median=float(np.median(ratios_a)),
                        pose_rmsratio_H=float(meanH_num_p / max(meanH_den, 1e-9)),
                        act_rmsratio_H=float(meanH_num_a / max(meanH_den, 1e-9)))
    del S
    gc.collect()
    return dict(route=rk, group=meta["group"], bands=res)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    results = {}
    if which in ("all", "p1"):
        results["part1_layaw_zero"] = part1_layaw_zero()
        json.dump(results, open(OUT / "results_p1.json", "w"), indent=1)
        print("part1 done")
    if which in ("all", "p2"):
        r2 = {}
        for rk, meta in V.ROUTES.items():
            if not (V.CACHE / f"{rk}.npz").exists():
                continue
            print("p2", rk, flush=True)
            r2[rk] = part2_event_gain(rk, meta)
        json.dump(r2, open(OUT / "results_p2.json", "w"), indent=1)
        print("part2 done")
    if which in ("all", "p3"):
        r3 = {}
        for rk, meta in V.ROUTES.items():
            if not (V.CACHE / f"{rk}.npz").exists():
                continue
            print("p3", rk, flush=True)
            r3[rk] = part3_tail_vs_mean(rk, meta)
        json.dump(r3, open(OUT / "results_p3.json", "w"), indent=1)
        print("part3 done")
    if which == "p3b":
        r3 = {}
        for rk, meta in V.ROUTES.items():
            if not (V.CACHE / f"{rk}.npz").exists():
                continue
            print("p3b", rk, flush=True)
            r3[rk] = part3_tail_vs_mean(rk, meta, vmin=10.0, pgate=0.02)
        json.dump(r3, open(OUT / "results_p3b.json", "w"), indent=1)
        print("part3b done")
