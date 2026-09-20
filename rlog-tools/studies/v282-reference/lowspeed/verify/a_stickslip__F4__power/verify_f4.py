import sys
sys.path.insert(0, '.')
from ss_load import load_all
from sslib import k_of_v
import numpy as np

EP, W, EX, VAL = load_all()
N = len(EP)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); route = col('route'); slip = col('slip'); j30 = col('j30')
kind = col('kind'); aa_abs = col('abs_aa')
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])

def ratio_stats(m, F=0.02):
    kk = k_of_v(v[m])
    twoFk = 2*F/kk
    r = slip[m] * kk / (2*F)
    return r, twoFk

print("=== INDEPENDENT RECOMPUTE of key ratios (F=0.02) ===")
for lo,hi in [(2,8),(8,15)]:
    m = TQ & (v>=lo) & (v<hi)
    r, twoFk = ratio_stats(m)
    print(f"{lo}-{hi} n={m.sum()}: p50={np.median(r):.3f} p90={np.percentile(r,90):.3f} frac>=1={np.mean(r>=1):.3f}")

print()
print("=== LEAVE-ONE-ROUTE-OUT (jackknife) on p50 and p90 ratio, 2-8 and 8-15 bins ===")
for lo,hi in [(2,8),(8,15)]:
    m = TQ & (v>=lo) & (v<hi)
    routes = np.unique(route[m])
    print(f"-- {lo}-{hi} m/s: {len(routes)} routes --")
    for rt in routes:
        mm = m & (route != rt)
        r, twoFk = ratio_stats(mm)
        n_drop = m.sum() - mm.sum()
        print(f"  drop {rt} (n_drop={n_drop}): n={mm.sum()} p50={np.median(r):.3f} p90={np.percentile(r,90):.3f}")

print()
print("=== Per-route breakdown (episode count, p50 ratio) to see which route dominates ===")
for lo,hi in [(2,8),(8,15)]:
    m = TQ & (v>=lo) & (v<hi)
    print(f"-- {lo}-{hi} --")
    for rt in np.unique(route[m]):
        mm = m & (route==rt)
        r,_ = ratio_stats(mm)
        print(f"  {rt}: n={mm.sum()} p50_ratio={np.median(r):.3f} p90_ratio={np.percentile(r,90) if mm.sum()>1 else float('nan'):.3f}")

print()
print("=== Sensitivity to F choice ===")
for lo,hi in [(2,8),(8,15)]:
    m = TQ & (v>=lo) & (v<hi)
    print(f"-- {lo}-{hi} --")
    for F in [0.015, 0.02, 0.025, 0.033, 0.045]:
        r,_ = ratio_stats(m, F=F)
        print(f"  F={F}: p50={np.median(r):.3f} p90={np.percentile(r,90):.3f} frac>=1={np.mean(r>=1):.3f}")
