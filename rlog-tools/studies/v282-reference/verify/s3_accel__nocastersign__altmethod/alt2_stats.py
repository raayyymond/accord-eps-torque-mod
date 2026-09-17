import json
import numpy as np
from scipy import stats

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s3_accel__nocastersign__altmethod/'
rows = json.load(open(OUT + 'alt2_events.json'))
rng = np.random.default_rng(11)


def cl_boot(sub, key, stat=np.nanmedian, NB=3000, r2min=None, r2key=None):
    def get(r):
        if r2min is not None and r2key is not None:
            r2 = r.get(r2key)
            if r2 is None or not np.isfinite(r2) or r2 < r2min:
                return np.nan
        return r.get(key, np.nan)
    x = np.array([get(r) for r in sub], float)
    routes = sorted(set(r['rk'] for r in sub))
    byr = {q: np.array([get(r) for r in sub if r['rk'] == q], float) for q in routes}
    bs = []
    for _ in range(NB):
        pick = rng.choice(routes, len(routes))
        z = np.concatenate([byr[p][rng.integers(0, len(byr[p]), len(byr[p]))] for p in pick])
        z = z[np.isfinite(z)]
        if len(z) >= 2:
            bs.append(stat(z))
    x = x[np.isfinite(x)]
    return (float(stat(x)) if len(x) else np.nan,
            float(np.nanpercentile(bs, 2.5)) if bs else np.nan,
            float(np.nanpercentile(bs, 97.5)) if bs else np.nan,
            int(len(x)))


def cl_boot_diff(A, B, key, stat=np.nanmedian, NB=3000, r2min=None, r2key=None):
    def get(r):
        if r2min is not None and r2key is not None:
            r2 = r.get(r2key)
            if r2 is None or not np.isfinite(r2) or r2 < r2min:
                return np.nan
        return r.get(key, np.nan)
    ax = np.array([get(r) for r in A], float); ax = ax[np.isfinite(ax)]
    bx = np.array([get(r) for r in B], float); bx = bx[np.isfinite(bx)]
    aroutes = sorted(set(r['rk'] for r in A)); broutes = sorted(set(r['rk'] for r in B))
    abyr = {q: np.array([get(r) for r in A if r['rk'] == q], float) for q in aroutes}
    bbyr = {q: np.array([get(r) for r in B if r['rk'] == q], float) for q in broutes}
    bs = []
    for _ in range(NB):
        pa = rng.choice(aroutes, len(aroutes)); pb = rng.choice(broutes, len(broutes))
        za = np.concatenate([abyr[p][rng.integers(0, len(abyr[p]), len(abyr[p]))] for p in pa])
        zb = np.concatenate([bbyr[p][rng.integers(0, len(bbyr[p]), len(bbyr[p]))] for p in pb])
        za = za[np.isfinite(za)]; zb = zb[np.isfinite(zb)]
        if len(za) >= 2 and len(zb) >= 2:
            bs.append(stat(zb) - stat(za))
    d0 = float(stat(bx) - stat(ax)) if len(ax) and len(bx) else np.nan
    return d0, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), len(ax), len(bx)


A = [r for r in rows if r['G'] == 'V282']
Aold = [r for r in rows if r['G'] == 'V282old']
B = [r for r in rows if r['G'] == 'TQ']
res = {}

print(f"n events with a return window >=0.3s: V282 {len(A)} V282old {len(Aold)} TQ {len(B)}")

print("\n=== fit quality (r2) so the tau numbers below aren't over-read ===")
for key in ("aa", "ap", "desired"):
    for G, sub in (("V282", A), ("V282old", Aold), ("TQ", B)):
        r2 = np.array([r.get(f"r2_{key}", np.nan) for r in sub], float)
        tau = np.array([r.get(f"tau_{key}", np.nan) for r in sub], float)
        nfit = np.isfinite(tau).sum()
        print(f"  {key:8s} {G:8s} n_attempt {len(sub)} n_fit {nfit} median r2 {np.nanmedian(r2):.2f} "
              f"(r2>=0.7: {int(np.nansum(r2 >= 0.7))})")

print("\n=== (a) decay time constant tau [s] of the RETURN (free-ish) window, median [route-cluster CI] ===")
print("     (only fits with r2 >= 0.5 kept; a caster deficit -> tau_achieved should exceed tau_desired MORE on TQ)")
for key in ("aa", "ap"):
    line = f"  tau_{key}"
    for G, sub in (("V282", A), ("V282old", Aold), ("TQ", B)):
        e = cl_boot(sub, f"tau_{key}", r2min=0.5, r2key=f"r2_{key}")
        res[f"{G}_tau_{key}"] = e
        line += f" | {G} {e[0]:.2f}[{e[1]:.2f},{e[2]:.2f}] n{e[3]}"
    print(line)
    line = f"  tau_desired (matched)"
for G, sub in (("V282", A), ("V282old", Aold), ("TQ", B)):
    e = cl_boot(sub, "tau_desired", r2min=0.5, r2key="r2_desired")
    res[f"{G}_tau_desired"] = e
    print(f"  tau_desired {G:8s} {e[0]:.2f}[{e[1]:.2f},{e[2]:.2f}] n{e[3]}")

print("\n=== dtau = tau_achieved - tau_desired, per event (r2>=0.5 both), median [CI], TQ-V282 diff ===")
for key in ("aa", "ap"):
    line = f"  dtau_{key}"
    for G, sub in (("V282", A), ("V282old", Aold), ("TQ", B)):
        def getdt(r, key=key):
            r2a = r.get(f"r2_{key}", np.nan); r2d = r.get("r2_desired", np.nan)
            if not (np.isfinite(r2a) and r2a >= 0.5 and np.isfinite(r2d) and r2d >= 0.5):
                return np.nan
            return r.get(f"dtau_{key}", np.nan)
        e = cl_boot(sub, None, stat=lambda z: np.nanmedian(z))  # placeholder, replaced below
        # cl_boot needs a key string; do it inline instead
        x = np.array([getdt(r) for r in sub], float)
        routes = sorted(set(r['rk'] for r in sub))
        byr = {q: np.array([getdt(r) for r in sub if r['rk'] == q], float) for q in routes}
        bs = []
        for _ in range(2000):
            pick = rng.choice(routes, len(routes))
            z = np.concatenate([byr[p][rng.integers(0, len(byr[p]), len(byr[p]))] for p in pick])
            z = z[np.isfinite(z)]
            if len(z) >= 2:
                bs.append(np.nanmedian(z))
        x = x[np.isfinite(x)]
        e = (float(np.nanmedian(x)) if len(x) else np.nan,
             float(np.nanpercentile(bs, 2.5)) if bs else np.nan,
             float(np.nanpercentile(bs, 97.5)) if bs else np.nan, int(len(x)))
        res[f"{G}_dtau_{key}"] = e
        line += f" | {G} {e[0]:+.2f}[{e[1]:+.2f},{e[2]:+.2f}] n{e[3]}"
    print(line)

print("\n=== (b) TRUE-ZERO overshoot: max deg past TRUE centre (not just past commanded) in the return tail ===")
for key in ("aa", "ap"):
    line = f"  truezero_ov_{key}"
    for G, sub in (("V282", A), ("V282old", Aold), ("TQ", B)):
        e = cl_boot(sub, f"truezero_overshoot_deg_{key}")
        res[f"{G}_truezero_ov_{key}"] = e
        line += f" | {G} {e[0]:.2f}[{e[1]:.2f},{e[2]:.2f}] n{e[3]}"
    d = cl_boot_diff(A, B, f"truezero_overshoot_deg_{key}")
    res[f"diff_TQ-V282_truezero_ov_{key}"] = d
    line += f" || TQ-V282 {d[0]:+.2f}[{d[1]:+.2f},{d[2]:+.2f}]"
    print(line)
    line = f"  truezero_negfrac_{key}"
    for G, sub in (("V282", A), ("V282old", Aold), ("TQ", B)):
        e = cl_boot(sub, f"truezero_negfrac_{key}")
        res[f"{G}_truezero_negfrac_{key}"] = e
        line += f" | {G} {e[0]:.2f}[{e[1]:.2f},{e[2]:.2f}] n{e[3]}"
    d = cl_boot_diff(A, B, f"truezero_negfrac_{key}")
    res[f"diff_TQ-V282_truezero_negfrac_{key}"] = d
    line += f" || TQ-V282 {d[0]:+.2f}[{d[1]:+.2f},{d[2]:+.2f}]"
    print(line)

print("\n=== proportion of events that overshoot true centre by >1 deg at all (event-count/nonlinear) ===")
for key in ("aa", "ap"):
    for G, sub in (("V282", A), ("V282old", Aold), ("TQ", B)):
        ov = np.array([r.get(f"truezero_overshoot_deg_{key}", np.nan) for r in sub], float)
        ov = ov[np.isfinite(ov)]
        frac = float(np.mean(ov > 1.0)) if len(ov) else np.nan
        print(f"  {key} {G:8s} frac>1deg {frac:.2f} (n{len(ov)})")

json.dump(res, open(OUT + 'alt2_results.json', 'w'), indent=1)
print("\nwrote", OUT + 'alt2_results.json')
