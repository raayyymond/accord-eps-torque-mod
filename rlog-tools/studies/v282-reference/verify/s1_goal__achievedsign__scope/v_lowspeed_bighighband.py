"""Adversarial SCOPE check on finding s1_goal/achieved-signal-crosscheck.

Claim under test: la_pose agrees with la_act within ~+/-0.1 (band |H|) at 0.05-0.6 Hz on V282/torque groups;
above 0.6 Hz at >15 m/s BOTH show |H| 1.3-4.3 vs model in EVERY group (a shared floor, not tracking signal).

SCOPE lens: the finding's magnitude table is entirely >=15 or >=22 m/s. Rev 6.4's specific complaints (large
angle self-centring, large-angle jerkiness, medium/large angle-RATE transients) live BELOW 15 m/s and at large
|model|/large steering angle. Does act vs pose still agree there? Does the >0.6 Hz "floor" still look like a
floor (same magnitude, uncorrelated with build) at low speed / large angle / inside jerk & accel EVENT windows,
or does it grow / change in a build-dependent way exactly where the complaints live -- which would falsify
"non-steering yaw content, a floor, same across builds" as the full story and mean the crosscheck was not
looking where the effect would live?

One route in RAM at a time. Writes v_results.json next to this script.
"""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

HERE = Path(__file__).resolve().parent
BANDS = [(0.05, 0.15), (0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.50)]
VB = [(0.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 99.0)]
VBN = ["0-8", "8-15", "15-22", ">22"]


def band_H_route(S, mask, f1, f2, ykey):
    """Single-route band_H using v282cmp.band_H over the usable runs restricted to mask, y=ykey vs model."""
    segs = []
    for i0, i1 in V.runs(mask, S["t"], min_s=8.0):
        x = np.nan_to_num(S["model"][i0:i1])
        y = np.nan_to_num(S[ykey][i0:i1])
        segs.append((x, y))
    return V.band_H(segs, f1, f2)


def event_window_check(S, route, group):
    """act vs pose agreement INSIDE jerk_events and accel_events windows (large-angle / large-rate, mixed speed)."""
    out = []
    ev, _ = V.jerk_events(S, jerk_thr=0.5, vmin=2.0)  # lowered thr per the brief's note that default is thin
    for e in ev:
        i0 = max(0, e["idx"] - int(1.5 * V.FS)); i1 = min(len(S["model"]), e["idx"] + int(3.0 * V.FS))
        x = np.nan_to_num(S["model"][i0:i1]); a = np.nan_to_num(S["la_act"][i0:i1]); p = np.nan_to_num(S["la_pose"][i0:i1])
        if len(x) < 50:
            continue
        rms_ap = float(np.sqrt(np.mean((a - p) ** 2)))
        rms_x = float(np.sqrt(np.mean(x ** 2))) + 1e-9
        corr = float(np.corrcoef(a, p)[0, 1]) if np.std(a) > 1e-6 and np.std(p) > 1e-6 else float("nan")
        out.append(dict(kind="jerk", route=route, group=group, v=e["v"], la_peak=e["la_peak"],
                         rms_act_minus_pose=rms_ap, rel_disagree=rms_ap / rms_x, corr_act_pose=corr))
    ae = V.accel_events(S, la_thr=1.2, vmin=2.0, min_hold=0.8)
    for e in ae:
        i0, i1 = e["i0"], e["i1"]
        x = np.nan_to_num(S["model"][i0:i1]); a = np.nan_to_num(S["la_act"][i0:i1]); p = np.nan_to_num(S["la_pose"][i0:i1])
        if len(x) < 50:
            continue
        rms_ap = float(np.sqrt(np.mean((a - p) ** 2)))
        rms_x = float(np.sqrt(np.mean(x ** 2))) + 1e-9
        corr = float(np.corrcoef(a, p)[0, 1]) if np.std(a) > 1e-6 and np.std(p) > 1e-6 else float("nan")
        out.append(dict(kind="accel", route=route, group=group, v=e["v"], la_peak=e["la_peak"],
                         rms_act_minus_pose=rms_ap, rel_disagree=rms_ap / rms_x, corr_act_pose=corr))
    return out


def main():
    res = dict(band_cells=[], events=[], la_yaw_check=[], amp_strat=[])
    for route, meta in V.ROUTES.items():
        group = meta["group"]
        cache = V.CACHE / f"{route}.npz"
        if not cache.exists():
            continue
        S = V.load(route)
        # 1. re-confirm la_yaw is identically zero (independent re-check, not trusting the finding's own number)
        res["la_yaw_check"].append(dict(route=route, group=group, std=float(np.nanstd(S["la_yaw"])),
                                        finite_frac=float(np.isfinite(S["la_yaw"]).mean())))
        base = V.usable(S)
        for vi, (v0, v1) in enumerate(VB):
            m = base & (S["v"] >= v0) & (S["v"] < v1)
            if m.sum() < 8 * V.FS:
                continue
            for f1, f2 in BANDS:
                ra = band_H_route(S, m, f1, f2, "la_act")
                rp = band_H_route(S, m, f1, f2, "la_pose")
                if ra is None or rp is None:
                    continue
                res["band_cells"].append(dict(route=route, group=group, vbin=VBN[vi], band=f"{f1}-{f2}",
                                              sec=ra["sec"], H_act=ra["H"], H_pose=rp["H"], coh_act=ra["coh"],
                                              coh_pose=rp["coh"], diff=rp["H"] - ra["H"]))
        # 2. large-|model| amplitude stratified check, LOW SPEED ONLY (<15 m/s) -- where self-centring/jerkiness
        #    complaints live. Envelope of 0.05-2.5Hz lowpassed model magnitude, tercile-free absolute bins.
        low = base & (S["v"] < 15.0)
        if low.sum() > 8 * V.FS:
            modlow = np.abs(np.nan_to_num(S["model"]))
            for lo, hi in [(0.0, 0.5), (0.5, 1.5), (1.5, 3.0), (3.0, 99.0)]:
                sel = low & (modlow >= lo) & (modlow < hi)
                if sel.sum() < 3 * V.FS:
                    continue
                x = np.nan_to_num(S["model"][sel]); a = np.nan_to_num(S["la_act"][sel]); p = np.nan_to_num(S["la_pose"][sel])
                sx = np.sign(x); sx[sx == 0] = 1
                res["amp_strat"].append(dict(route=route, group=group, lo=lo, hi=hi, sec=float(sel.sum() / V.FS),
                                              secant_act=float(np.sum(a * sx) / np.sum(np.abs(x))),
                                              secant_pose=float(np.sum(p * sx) / np.sum(np.abs(x))),
                                              rms_act_minus_pose=float(np.sqrt(np.mean((a - p) ** 2)))))
        # 3. event-window check (mixed speed, but the events ARE where large angle/rate transients live)
        res["events"] += event_window_check(S, route, group)
        del S
        print("done", route, group, flush=True)
    json.dump(res, open(HERE / "v_results.json", "w"), indent=1)
    print("wrote v_results.json", len(res["band_cells"]), "band cells,", len(res["events"]), "events,",
          len(res["amp_strat"]), "amp-strat rows")


if __name__ == "__main__":
    main()
