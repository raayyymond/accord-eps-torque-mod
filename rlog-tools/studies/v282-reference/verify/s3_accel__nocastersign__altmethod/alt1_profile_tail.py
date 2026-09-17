"""ALTMETHOD pass on the finding 'no-caster-signature-beyond-lag' (stream s3_accel).
Uses the ALREADY-COMPUTED s3_pass2.json (no re-load of routes -> RAM-safe), but applies a genuinely
DIFFERENT estimator than s3_pass2_stats.py's mean-based lag-sweep + linear-gain approach:

 (1) TAIL, not mean: pull out just the near-zero angle bin (fr in [0.1,0.2), the last ~10-20% of the
     unwind before centre) from the already-built error-vs-|desired|/P profile, instead of averaging
     error over the whole build/unwind phase. A caster deficit ("ignores self-centring") should be a
     LOCALISED effect concentrated near centre, not a uniform bias -- a phase-mean can dilute it.
 (2) LOCALISED-vs-UNIFORM: near-zero-bin minus the mean of the other 8 bins, per event. This isolates a
     bin-localised kink from a flat DC offset (which the original 'sym' statistic already covered).
 (3) ROBUST/rank: median + route-clustered bootstrap (not mean), plus a distribution-free Brunner-Munzel
     rank test pooled over events (ignoring route clustering, as an independent check), and the 90th
     percentile of |unwind error| per group (a tail statistic: does a MINORITY of severe events carry a
     signature the mean misses?).
 (4) EVENT-COUNT / classification: fraction of events whose return-overshoot exceeds a fixed absolute
     threshold, TQ vs V282, via a bootstrap on the proportion difference (nonlinear, not a linear mean).
"""
import json, sys
import numpy as np
from scipy import stats

OUT_S3 = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel/out/'
OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s3_accel__nocastersign__altmethod/'

D = json.load(open(OUT_S3 + 's3_pass2.json'))
rows = D['rows']
FB = D['fbins']
GM = {"V282": "V282", "V282old": "V282old", "T64": "TQ", "T64B": "TQ", "T5": "TQ", "T4": "TQ"}
for r in rows:
    r['G'] = GM[r['group']]

rng = np.random.default_rng(7)
res = {}


def cl_boot(sub, get, stat=np.nanmedian, NB=3000):
    x = np.array([get(r) for r in sub], float)
    routes = sorted(set(r['rk'] for r in sub))
    byr = {q: np.array([get(r) for r in sub if r['rk'] == q], float) for q in routes}
    bs = []
    for _ in range(NB):
        pick = rng.choice(routes, len(routes))
        z = np.concatenate([byr[p][rng.integers(0, len(byr[p]), len(byr[p]))] for p in pick])
        if np.isfinite(z).sum() >= 2:
            bs.append(stat(z))
    x = x[np.isfinite(x)]
    return float(stat(x)) if len(x) else np.nan, float(np.nanpercentile(bs, 2.5)) if bs else np.nan, \
        float(np.nanpercentile(bs, 97.5)) if bs else np.nan, int(len(x))


def cl_boot_diff(A, B, get, stat=np.nanmedian, NB=3000):
    """route-clustered bootstrap of stat(B)-stat(A), NOT stratified (deliberately different machinery
    from s3_pass2_stats.strat, which weights v/P strata cells; here we just check group medians)."""
    a0, _, _, _ = cl_boot(A, get, stat, NB=1)
    b0, _, _, _ = cl_boot(B, get, stat, NB=1)
    ax = np.array([get(r) for r in A], float); bx = np.array([get(r) for r in B], float)
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
    d0 = float(stat(bx[np.isfinite(bx)]) - stat(ax[np.isfinite(ax)]))
    return d0, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), len(ax), len(bx)


A = [r for r in rows if r['G'] == 'V282']
B = [r for r in rows if r['G'] == 'TQ']
Aold = [r for r in rows if r['G'] == 'V282old']

print(f"n events: V282 {len(A)}  V282old {len(Aold)}  TQ {len(B)}")
print("\nfbins (fraction of peak |desired|/P):", FB)

# ---------------- (1)+(2) tail bin + localised-vs-uniform, per key/phase ----------------
print("\n=== (1) TAIL: near-zero angle bin (fr 0.1-0.2) error/P, median [route-cluster CI], group and TQ-V282 diff ===")
for key in ("aa", "ap"):
    for ph in ("build", "unwind"):
        def getbin0(r, key=key, ph=ph):
            v = r[f"{key}_c25_prof_{ph}"][0]
            return v if v is not None else np.nan
        line = f"  {key} {ph:6s} bin0(0.1-0.2)"
        for G, sub in (("V282", A), ("V282old", Aold), ("TQ", B)):
            e = cl_boot(sub, getbin0)
            res[f"{G}_{key}_{ph}_bin0"] = e
            line += f" | {G} {e[0]:+.3f}[{e[1]:+.3f},{e[2]:+.3f}] n{e[3]}"
        d = cl_boot_diff(A, B, getbin0)
        res[f"diff_TQ-V282_{key}_{ph}_bin0"] = d
        line += f" || TQ-V282 {d[0]:+.3f}[{d[1]:+.3f},{d[2]:+.3f}] nA{d[3]} nB{d[4]}"
        print(line)

print("\n=== (2) LOCALISED-vs-UNIFORM: (near-zero bin) - (mean of other 8 bins), per event, median [CI] ===")
for key in ("aa", "ap"):
    for ph in ("build", "unwind"):
        def getlocal(r, key=key, ph=ph):
            prof = np.array(r[f"{key}_c25_prof_{ph}"], float)
            if not np.isfinite(prof[0]):
                return np.nan
            rest = prof[1:]
            rest = rest[np.isfinite(rest)]
            if len(rest) < 3:
                return np.nan
            return float(prof[0] - np.mean(rest))
        line = f"  {key} {ph:6s} bin0-rest"
        for G, sub in (("V282", A), ("V282old", Aold), ("TQ", B)):
            e = cl_boot(sub, getlocal)
            res[f"{G}_{key}_{ph}_bin0minusrest"] = e
            line += f" | {G} {e[0]:+.3f}[{e[1]:+.3f},{e[2]:+.3f}] n{e[3]}"
        d = cl_boot_diff(A, B, getlocal)
        res[f"diff_TQ-V282_{key}_{ph}_bin0minusrest"] = d
        line += f" || TQ-V282 {d[0]:+.3f}[{d[1]:+.3f},{d[2]:+.3f}]"
        print(line)

# ---------------- (3) robust/rank/tail ----------------
print("\n=== (3a) Brunner-Munzel rank test (pooled events, no route clustering -- independent check), sym @ L=0.25 ===")
for key in ("aa", "ap"):
    xa = np.array([r[f"{key}_L0.25_sym"] for r in A], float); xa = xa[np.isfinite(xa)]
    xb = np.array([r[f"{key}_L0.25_sym"] for r in B], float); xb = xb[np.isfinite(xb)]
    bm = stats.brunnermunzel(xa, xb)
    mw = stats.mannwhitneyu(xa, xb, alternative='two-sided')
    print(f"  {key} sym L0.25: V282 median {np.median(xa):+.3f} n{len(xa)}  TQ median {np.median(xb):+.3f} n{len(xb)}  "
          f"BM stat {bm.statistic:.2f} p {bm.pvalue:.3f}  MWU p {mw.pvalue:.3f}")
    res[f"BM_{key}_sym"] = dict(stat=float(bm.statistic), p=float(bm.pvalue), mwu_p=float(mw.pvalue),
                                 medA=float(np.median(xa)), medB=float(np.median(xb)))

print("\n=== (3b) 90th percentile of |unwind error| (tail severity), group, and TQ-V282 diff of the 90th pctile ===")
for key in ("aa", "ap"):
    def getabsu(r, key=key):
        v = r[f"{key}_L0.25_unwind"]
        return abs(v) if v is not None and np.isfinite(v) else np.nan
    line = f"  {key} |unwind_err| p90"
    for G, sub in (("V282", A), ("V282old", Aold), ("TQ", B)):
        e = cl_boot(sub, getabsu, stat=lambda z: np.nanpercentile(z, 90))
        res[f"{G}_{key}_absunwind_p90"] = e
        line += f" | {G} {e[0]:.3f}[{e[1]:.3f},{e[2]:.3f}] n{e[3]}"
    d = cl_boot_diff(A, B, getabsu, stat=lambda z: np.nanpercentile(z, 90))
    res[f"diff_TQ-V282_{key}_absunwind_p90"] = d
    line += f" || TQ-V282 {d[0]:+.3f}[{d[1]:+.3f},{d[2]:+.3f}]"
    print(line)

# ---------------- (4) event-count / classification on overshoot ----------------
print("\n=== (4) fraction of events with return-overshoot > threshold (deg), bootstrap on the proportion ===")
for key in ("aa", "ap"):
    for thr in (0.5, 1.0, 2.0):
        def flag(r, key=key, thr=thr):
            v = r.get(f"{key}_ret_overshoot_deg")
            # ret_overshoot_deg not stored in pass2.json rows (that's pass1/metrics()); guard
            return np.nan
        pass
print("  (ret_overshoot_deg is not in s3_pass2.json rows -- see alt2_decay_refit.py for a re-derived, event-level overshoot/decay check from raw signals)")

json.dump(res, open(OUT + 'alt1_results.json', 'w'), indent=1)
print("\nwrote", OUT + 'alt1_results.json')
