"""Part 2: (b) la_act vs curvature*v^2 exactness, AND whether the whole-route correlation could be
masking a real event-specific (high-jerk-transient) discrepancy that matters for the notes this
finding says are voided. Power question: full-route N is huge (tens of thousands of samples,
dominated by low lateral-accel/cruise), while the jerk-event windows the substantive stream cares
about are a tiny fraction of that. Does the tight overall corr/slope actually bound the residual
during the events themselves?
"""
import sys, json, gc
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

report = {}
for rk in V.ROUTES:
    try:
        S = V.load(rk)
    except FileNotFoundError:
        continue
    u = V.usable(S)
    curv_la = S['model'][u]  # cs_des_curv*v*v is the MODEL desired, not the same field; need la_act vs curvature*v^2 directly
    # la_act should equal controlsState curvature * v^2 (per finding). We don't have raw curvature field in S,
    # but we can regress la_act on model isn't the same thing. Instead verify la_act vs la_pose residual,
    # conditioned on |jerk| percentile, to see if agreement DEGRADES specifically during high-jerk transients.
    la_act = np.nan_to_num(S['la_act'][u])
    la_pose = np.nan_to_num(S['la_pose'][u])
    jerk = np.abs(V.deriv(V.lowpass(np.nan_to_num(S['model']), 2.0)))[u]
    v = S['v'][u]
    ok = (np.abs(la_act) > 0.05) | (np.abs(la_pose) > 0.05)
    la_act, la_pose, jerk, v = la_act[ok], la_pose[ok], jerk[ok], v[ok]
    if len(la_act) < 100:
        del S; gc.collect(); continue
    resid = la_pose - la_act
    # bucket by jerk percentile within this route
    qs = np.nanpercentile(jerk, [50, 90, 99]) if len(jerk) > 20 else [np.nan]*3
    lo_mask = jerk < qs[0]
    hi_mask = jerk > qs[2]
    def stats(mask):
        if mask.sum() < 20:
            return dict(n=int(mask.sum()))
        r = resid[mask]; a = la_act[mask]
        corr = float(np.corrcoef(la_act[mask], la_pose[mask])[0, 1]) if np.std(a) > 1e-6 else float('nan')
        slope = float(np.polyfit(a, la_pose[mask], 1)[0]) if np.std(a) > 1e-6 else float('nan')
        return dict(n=int(mask.sum()), rms_resid=float(np.sqrt(np.mean(r**2))),
                     corr=corr, slope=slope, rms_la_act=float(np.sqrt(np.mean(a**2))))
    report[rk] = dict(group=S['meta']['group'], overall=stats(np.ones(len(la_act), bool)),
                       low_jerk=stats(lo_mask), high_jerk=stats(hi_mask),
                       n_overall=len(la_act), n_high_jerk=int(hi_mask.sum()))
    del S, la_act, la_pose, jerk, v, resid
    gc.collect()

print(json.dumps(report, indent=1))
with open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s2_jerk__instrumentde__power/b_la_act_vs_pose_by_jerk.json', 'w') as f:
    json.dump(report, f, indent=1)
