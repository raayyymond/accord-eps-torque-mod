import sys
sys.path.insert(0, "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip")
from ss_load import load_all
from sslib import k_of_v
import numpy as np

EP, W, EX, VAL = load_all()
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); route = col('route'); slip = col('slip')
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])

F=0.02
for lo,hi in [(2,8),(8,15)]:
    m = TQ & (v>=lo)&(v<hi)
    kk = k_of_v(v[m]); r = slip[m]*kk/(2*F)
    reach = r>=1
    print(f"{lo}-{hi}: n={m.sum()} n_reach={reach.sum()} frac={reach.mean():.3f}")
    rr = route[m]
    for rt in np.unique(rr):
        rm = rr==rt
        print(f"   {rt}: n={rm.sum()} reach={reach[rm].sum()} frac={reach[rm].mean():.3f}")
    # bootstrap CI on the fraction itself, route-cluster
    u = np.unique(rr); rng=np.random.default_rng(3); idx={c:np.where(rr==c)[0] for c in u}
    bs=[]
    for _ in range(5000):
        pick = rng.choice(u,len(u))
        ii = np.concatenate([idx[c] for c in pick])
        bs.append(reach[ii].mean())
    bs=np.array(bs)
    print(f"   frac boot CI [2.5,97.5] = {np.percentile(bs,[2.5,97.5])}, frac(boot>=0.5)={np.mean(bs>=0.5):.4f}")
