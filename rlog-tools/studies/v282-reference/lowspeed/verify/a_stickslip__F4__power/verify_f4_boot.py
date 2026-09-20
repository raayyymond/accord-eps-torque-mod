import sys
sys.path.insert(0, "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip")
from ss_load import load_all
from sslib import k_of_v
import numpy as np

EP, W, EX, VAL = load_all()
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); route = col('route'); slip = col('slip')
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])

def boot_dist(m, F=0.02, nb=5000, seed=2):
    kk = k_of_v(v[m]); r = slip[m]*kk/(2*F)
    rr = route[m]; u = np.unique(rr); rng = np.random.default_rng(seed)
    idx = {c: np.where(rr==c)[0] for c in u}
    p50s=[]; p90s=[]
    for _ in range(nb):
        pick = rng.choice(u, len(u))
        ii = np.concatenate([idx[c] for c in pick])
        p50s.append(np.median(r[ii])); p90s.append(np.percentile(r[ii],90))
    return np.array(p50s), np.array(p90s)

for lo,hi in [(2,8),(8,15)]:
    m = TQ & (v>=lo)&(v<hi)
    p50s,p90s = boot_dist(m)
    print(f"{lo}-{hi} n={m.sum()} nroutes={len(np.unique(route[m]))}")
    print(f"  p50 boot: mean={p50s.mean():.3f} 2.5/97.5={np.percentile(p50s,[2.5,97.5])} frac(p50>=1)={np.mean(p50s>=1):.4f}")
    print(f"  p90 boot: mean={p90s.mean():.3f} 2.5/97.5={np.percentile(p90s,[2.5,97.5])} frac(p90>=1)={np.mean(p90s>=1):.4f}")
    # number of unique route-resample compositions actually possible
    print(f"  distinct bootstrap p90 values: {len(np.unique(np.round(p90s,3)))}")
