"""Independent re-derivation of the 'v282-large-angle-reference-is-driver-assisted' finding.
Re-uses s3turns.find_turns (the shared event detector) but does NOT reuse s3_stats.py's
aggregation -- recomputes press-fraction counts and stats from scratch, with an explicit,
stated window definition, to check whether the magnitude ("171/202 pressed somewhere",
"only 3 fully hands-off", the median press-fraction numbers) survives.

Run one route at a time (RAM discipline), accumulate only small per-event dicts.
"""
import sys, json
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import s3turns as T
import v282cmp as V

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s3_accel__v282largeang__method/'

FS = V.FS
rows = []
cand_all = {}  # rk -> total peaks found by find_peaks BEFORE any filter (candidates before speed gate)
from scipy import signal

for rk in V.ROUTES:
    R = T.prep(rk)
    # 1) reproduce the raw peak count (before vmin/vmax speed gate) to check the "202" denominator
    adl = V.lowpass(R["ad"], 1.0)
    a = np.abs(adl)
    pk, _ = signal.find_peaks(a, height=25.0, prominence=0.6 * 25.0, distance=int(3 * FS))
    cand_all[rk] = int(len(pk))

    # 2) run the SAME event detector as s3_run.py (shared library function -- not reimplemented)
    evs, rej = T.find_turns(R)
    n = len(R["t"])
    for e in evs:
        i, j = e["i"], e["j"]
        ret_end = j + int(3 * FS)  # return window used by s3turns' own e["press_frac"]
        # exact window as s3turns defines it: [i, j+3s)
        w_exact = R["pressed"][i:ret_end]
        # padded window per the finding's stated definition: [build_start-1s, return_end+1s]
        pad = int(1 * FS)
        lo = max(0, i - pad); hi = min(n, ret_end + pad)
        w_pad = R["pressed"][lo:hi]
        rows.append(dict(
            rk=rk, group=R["group"], v=e["v"], P=e["P"],
            press_frac_exact=float(w_exact.mean()) if len(w_exact) else np.nan,
            press_any_exact=bool(w_exact.any()) if len(w_exact) else None,
            press_frac_pad=float(w_pad.mean()) if len(w_pad) else np.nan,
            press_any_pad=bool(w_pad.any()) if len(w_pad) else None,
            press_build=float(R["pressed"][e["i"]:e["h0"]].mean()) if e["h0"] - e["i"] >= 1 else np.nan,
            press_hold=float(R["pressed"][e["h0"]:e["h1"]].mean()) if e["h1"] - e["h0"] >= 1 else np.nan,
            press_unwind=float(R["pressed"][e["h1"]:e["j"]].mean()) if e["j"] - e["h1"] >= 1 else np.nan,
            press_ret=float(R["pressed"][e["j"]:ret_end].mean()) if ret_end - e["j"] >= 1 else np.nan,
        ))
    print(rk, R["group"], "kept", len(evs), "candidates(pre-speed-gate)", cand_all[rk], flush=True)
    del R

print()
print("total events (kept, same detector as s3_run.py):", len(rows))
print("sum of pre-speed-gate find_peaks candidates over all routes:", sum(cand_all.values()))
print("sum of find_turns' own post-speed-gate 'candidates' counter would be the s3_run.py rejects['candidates'] sum")

n_tot = len(rows)
n_any_exact = sum(1 for r in rows if r["press_any_exact"])
n_any_pad = sum(1 for r in rows if r["press_any_pad"])
n_hands_off_exact = n_tot - n_any_exact
n_hands_off_pad = n_tot - n_any_pad
print(f"\nusing EXACT window [build_start, return_end+3s) (s3turns' own e['press_frac'] window):")
print(f"  events with >=1 pressed frame somewhere: {n_any_exact}/{n_tot}")
print(f"  fully hands-off: {n_hands_off_exact}/{n_tot}")
print(f"\nusing PADDED window [build_start-1s, return_end+3s+1s) (finding's stated definition):")
print(f"  events with >=1 pressed frame somewhere: {n_any_pad}/{n_tot}")
print(f"  fully hands-off: {n_hands_off_pad}/{n_tot}")

# per-group fully hands-off counts (padded window, matches finding's per-group breakdown attempt)
groups = sorted(set(r["group"] for r in rows))
print("\nper-group fully-hands-off counts (padded window):")
for g in groups:
    sub = [r for r in rows if r["group"] == g]
    ho = sum(1 for r in sub if not r["press_any_pad"])
    print(f"  {g:8s} n={len(sub):3d}  fully_hands_off={ho}")

# median press_frac per group + bootstrap CI over events (simple, unclustered -- flag if it disagrees with route-clustered)
rng = np.random.default_rng(7)
def med_ci(x, nb=4000):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 3:
        return dict(n=len(x), med=float(np.median(x)) if len(x) else np.nan)
    est = float(np.median(x))
    bs = [np.median(x[rng.integers(0, len(x), len(x))]) for _ in range(nb)]
    return dict(n=len(x), med=est, ci=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])

print("\nmedian press_frac (EXACT window) by V282 vs torque (event-level bootstrap, NOT route-clustered):")
GM = {"V282": "V282", "V282old": "V282old", "T64": "torque", "T64B": "torque", "T5": "torque", "T4": "torque"}
for g in ["V282", "V282old", "torque"]:
    sub = [r["press_frac_exact"] for r in rows if GM[r["group"]] == g]
    print(f"  {g:8s} {med_ci(sub)}")

print("\nmedian press_build / press_unwind by V282 vs torque:")
for phase in ("press_build", "press_unwind", "press_hold", "press_ret"):
    print(f" {phase}")
    for g in ["V282", "torque"]:
        sub = [r[phase] for r in rows if GM[r["group"]] == g]
        print(f"    {g:8s} {med_ci(sub)}")

# route-clustered bootstrap (matches s3_stats.py's clustering scheme) for press_frac_exact
def route_cluster_ci(sub_rows, key, nb=4000):
    routes = sorted(set(r["rk"] for r in sub_rows))
    byr = {rk: np.array([r[key] for r in sub_rows if r["rk"] == rk], float) for rk in routes}
    byr = {rk: v[np.isfinite(v)] for rk, v in byr.items()}
    byr = {rk: v for rk, v in byr.items() if len(v)}
    if not byr:
        return None
    all_v = np.concatenate(list(byr.values()))
    est = float(np.median(all_v))
    routes2 = list(byr.keys())
    bs = []
    for _ in range(nb):
        pick = rng.choice(routes2, len(routes2))
        z = np.concatenate([byr[p][rng.integers(0, len(byr[p]), len(byr[p]))] for p in pick])
        bs.append(np.median(z))
    return dict(n=len(all_v), routes=len(routes2), est=est, ci=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])

print("\nroute-clustered bootstrap median press_frac_exact:")
for g in ["V282", "torque"]:
    sub = [r for r in rows if GM[r["group"]] == g]
    print(f"  {g:8s} {route_cluster_ci(sub, 'press_frac_exact')}")

# stratified diff (crude: unweighted, since finding cites a stratified number -0.097)
def strat_diff_simple(A, B, key, vb_key="v", p_key="P", nb=4000):
    def vb(v): return 0 if v < 5 else (1 if v < 8 else 2)
    def pb(p): return 0 if p < 60 else (1 if p < 150 else 2)
    cells = {}
    for r in A:
        cells.setdefault((vb(r[vb_key]), pb(r[p_key])), [[], []])[0].append(r[key])
    for r in B:
        cells.setdefault((vb(r[vb_key]), pb(r[p_key])), [[], []])[1].append(r[key])
    use = {c: (np.array(a, float), np.array(b, float)) for c, (a, b) in cells.items()}
    use = {c: (a[np.isfinite(a)], b[np.isfinite(b)]) for c, (a, b) in use.items()}
    use = {c: ab for c, ab in use.items() if len(ab[0]) >= 2 and len(ab[1]) >= 2}
    if not use:
        return None
    w = {c: min(len(a), len(b)) for c, (a, b) in use.items()}
    W = sum(w.values())
    def est_fn(sampler):
        return sum(w[c] * (np.mean(sampler(b)) - np.mean(sampler(a))) for c, (a, b) in use.items()) / W
    e0 = est_fn(lambda x: x)
    bs = [est_fn(lambda x: x[rng.integers(0, len(x), len(x))]) for _ in range(nb)]
    return dict(diff=float(e0), ci=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                n_matched=int(W), cells={str(c): (len(a), len(b)) for c, (a, b) in use.items()})

A = [r for r in rows if r["group"] == "V282"]
B = [r for r in rows if GM[r["group"]] == "torque"]
print("\nstratified (speed x peak) mean diff, torque - V282, press_frac_exact:")
print(" ", strat_diff_simple(A, B, "press_frac_exact"))
print("\nstratified mean diff, torque - V282, press_build:")
print(" ", strat_diff_simple(A, B, "press_build"))
print("\nstratified mean diff, torque - V282, press_unwind:")
print(" ", strat_diff_simple(A, B, "press_unwind"))

json.dump(dict(rows=rows, cand_all=cand_all, n_tot=n_tot, n_any_exact=n_any_exact, n_any_pad=n_any_pad),
          open(OUT + "verify_out.json", "w"), indent=1, default=float)
print("\nwrote", OUT + "verify_out.json")
