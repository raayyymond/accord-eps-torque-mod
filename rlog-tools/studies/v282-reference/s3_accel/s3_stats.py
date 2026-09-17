"""Group summaries with two bootstraps (events; routes-then-events) and speed x peak-angle stratified V282-vs-torque contrasts."""
import json, sys
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')
import s3turns as T

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel/out/'
D = json.load(open(OUT + 'turn_events.json'))
rows = D["rows"]
for r in rows:
    r["vb"], r["pb"] = T.strata(r)
    r["G"] = {"V282": "V282", "V282old": "V282old", "T64": "T6.4", "T64B": "T6.4", "T5": "T4-5", "T4": "T4-5"}[r["group"]]
    r["TQ"] = r["group"].startswith("T")
rng = np.random.default_rng(1)
NB = 2000

METRICS = ["press_frac", "press_build", "press_hold", "press_unwind", "press_ret",
           "drv_build", "drv_hold", "drv_unwind", "drv_ret",
           "aa_build_err", "aa_hold_err", "aa_unwind_err", "aa_ret_err",
           "ap_build_err", "ap_hold_err", "ap_unwind_err", "ap_ret_err",
           "aa_build_errdeg", "aa_hold_errdeg", "aa_unwind_errdeg",
           "aa_build_gain", "aa_unwind_gain", "ap_build_gain", "ap_unwind_gain",
           "aa_build_err_nolag", "aa_unwind_err_nolag", "aa_hold_err_nolag",
           "aa_ret_overshoot", "aa_ret_overshoot_deg", "ap_ret_overshoot", "aa_settle_s", "ap_settle_s", "aa_peak_ratio", "ap_peak_ratio",
           "hf_build", "hf_hold", "hf_unwind", "hfn_build", "hfn_unwind", "dwell_build", "dwell_unwind",
           "hold_share_f", "hold_share_p", "hold_share_i", "hold_out"]


def vals(sub, k):
    return np.array([r.get(k, np.nan) for r in sub], float)


def boot(sub, k, stat=np.nanmedian):
    x = vals(sub, k); ok = np.isfinite(x)
    if ok.sum() < 3:
        return dict(n=int(ok.sum()), est=float(stat(x)) if ok.any() else np.nan)
    est = float(stat(x))
    ev = [stat(x[rng.integers(0, len(x), len(x))]) for _ in range(NB)]
    routes = sorted(set(r["rk"] for r in sub))
    byr = {rk: np.array([r.get(k, np.nan) for r in sub if r["rk"] == rk], float) for rk in routes}
    cl = []
    for _ in range(NB):
        pick = rng.choice(routes, len(routes))
        z = np.concatenate([byr[p][rng.integers(0, len(byr[p]), len(byr[p]))] for p in pick])
        cl.append(stat(z))
    return dict(n=int(ok.sum()), routes=len(routes), est=est,
                ci_ev=[float(np.nanpercentile(ev, 2.5)), float(np.nanpercentile(ev, 97.5))],
                ci_route=[float(np.nanpercentile(cl, 2.5)), float(np.nanpercentile(cl, 97.5))])


def strat_diff(A, B, k):
    """Stratified (speed x peak) difference of MEANS, B - A, weighted by min(nA, nB) per cell; bootstrap resamples within cells."""
    cells = {}
    for r in A + B:
        cells.setdefault((r["vb"], r["pb"]), [[], []])[0 if r in A else 1].append(r.get(k, np.nan))
    use = {c: (np.array(a, float), np.array(b, float)) for c, (a, b) in cells.items()
           if np.isfinite(a).sum() >= 2 and np.isfinite(b).sum() >= 2}
    if not use:
        return None
    w = {c: min(np.isfinite(a).sum(), np.isfinite(b).sum()) for c, (a, b) in use.items()}
    W = sum(w.values())

    def est(sampler):
        return sum(w[c] * (np.nanmean(sampler(b)) - np.nanmean(sampler(a))) for c, (a, b) in use.items()) / W
    e0 = est(lambda x: x)
    bs = [est(lambda x: x[rng.integers(0, len(x), len(x))]) for _ in range(NB)]
    return dict(diff=float(e0), ci=[float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5))],
                cells={f"{T.VB[c[0]]}|{T.PB[c[1]]}": [int(np.isfinite(a).sum()), int(np.isfinite(b).sum())] for c, (a, b) in use.items()},
                n_matched=int(W))


res = dict(counts={}, groups={}, contrasts={})
for G in ["V282", "V282old", "T6.4", "T4-5", "TQall"]:
    sub = [r for r in rows if (r["TQ"] if G == "TQall" else r["G"] == G)]
    cnt = np.zeros((3, 3), int)
    for r in sub:
        cnt[r["vb"], r["pb"]] += 1
    res["counts"][G] = dict(n=len(sub), routes=len(set(r["rk"] for r in sub)), grid_speed_x_peak=cnt.tolist(),
                            median_v=float(np.median(vals(sub, "v"))), median_P=float(np.median(vals(sub, "P"))))
    res["groups"][G] = {k: boot(sub, k) for k in METRICS}
A = [r for r in rows if r["G"] == "V282"]
for name, B in [("T6.4-V282", [r for r in rows if r["G"] == "T6.4"]), ("TQall-V282", [r for r in rows if r["TQ"]]),
                ("V282old-V282", [r for r in rows if r["G"] == "V282old"])]:
    res["contrasts"][name] = {k: strat_diff(A, B, k) for k in METRICS}
res["rejects"] = D["rejects"]
json.dump(res, open(OUT + 's3_stats.json', 'w'), indent=1)

print("counts (rows speed 2.5-5/5-8/8-15, cols peak 25-60/60-150/150+):")
for G, c in res["counts"].items():
    print(f"  {G:8s} n={c['n']:3d} routes={c['routes']} vmed={c['median_v']:.1f} Pmed={c['median_P']:.0f} grid={c['grid_speed_x_peak']}")
print()
hdr = f"{'metric':24s}" + "".join(f"{G:>30s}" for G in ["V282", "V282old", "T6.4", "T4-5", "TQall"])
print(hdr)
for k in METRICS:
    line = f"{k:24s}"
    for G in ["V282", "V282old", "T6.4", "T4-5", "TQall"]:
        b = res["groups"][G][k]
        if "ci_route" in b:
            line += f"  {b['est']:+7.3f} [{b['ci_route'][0]:+.2f},{b['ci_route'][1]:+.2f}]n{b['n']:2d}"
        else:
            line += f"{'n<3':>30s}"
    print(line)
print()
for name, C in res["contrasts"].items():
    print("stratified mean difference", name)
    for k, c in C.items():
        if c:
            flag = " *" if (c["ci"][0] > 0 or c["ci"][1] < 0) else ""
            print(f"   {k:24s} {c['diff']:+8.3f} [{c['ci'][0]:+.3f},{c['ci'][1]:+.3f}] matched={c['n_matched']}{flag}")
